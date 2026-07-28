import { useCallback, useRef, useState } from "react";

const WS_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000")
  .replace(/^http/, "ws")
  .concat("/api/transcribe/live");

/**
 * Dictation that shows the words as they land.
 *
 * The audio graph asks for a 16 kHz `AudioContext` outright, which is the rate
 * the model wants, so there is no resampling to do in JavaScript. An
 * `AudioWorklet` runs the capture on the audio thread — a `ScriptProcessorNode`
 * would run on the main thread and drop samples whenever React rendered.
 *
 * Text comes back a phrase at a time, as the server's voice-activity detector
 * closes each segment. `onSegment` appends; the caller owns the transcript.
 */
export function useDictation(onSegment: (text: string) => void) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const teardown = useRef<(() => void) | null>(null);
  // Kept in a ref so the worklet callback always sees the current callback
  // without tearing down and rebuilding the audio graph on every render.
  const emit = useRef(onSegment);
  emit.current = onSegment;

  const stop = useCallback(() => {
    teardown.current?.();
    teardown.current = null;
    setRecording(false);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    let stream: MediaStream | undefined;
    let context: AudioContext | undefined;
    let socket: WebSocket | undefined;

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      context = new AudioContext({ sampleRate: 16000 });
      await context.audioWorklet.addModule("/capture-worklet.js");

      socket = new WebSocket(WS_URL);
      socket.binaryType = "arraybuffer";

      await new Promise<void>((resolve, reject) => {
        socket!.onopen = () => resolve();
        socket!.onerror = () => reject(new Error("Could not reach the transcriber."));
      });

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "segment" && message.text) emit.current(message.text);
        else if (message.type === "error") setError(new Error(message.detail));
      };

      const source = context.createMediaStreamSource(stream);
      const capture = new AudioWorkletNode(context, "capture");
      capture.port.onmessage = (event) => {
        if (socket?.readyState === WebSocket.OPEN) socket.send(event.data);
      };
      source.connect(capture);

      teardown.current = () => {
        // Ask for the tail before closing: the last phrase is still buffered in
        // the detector, and dropping it is the one thing a dictation UI must
        // never do.
        if (socket?.readyState === WebSocket.OPEN) socket.send("stop");
        capture.port.onmessage = null;
        source.disconnect();
        capture.disconnect();
        stream?.getTracks().forEach((track) => track.stop());
        setTimeout(() => {
          socket?.close();
          void context?.close();
        }, 1200);
      };
      setRecording(true);
    } catch (failure) {
      setError(failure);
      stream?.getTracks().forEach((track) => track.stop());
      void context?.close();
      socket?.close();
    }
  }, []);

  const toggle = useCallback(() => (recording ? stop() : start()), [recording, start, stop]);

  return { recording, error, toggle };
}
