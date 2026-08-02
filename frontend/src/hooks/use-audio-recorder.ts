import { useEffect, useRef, useState } from "react";
import { ApiError, WS_URL } from "@/lib/api";

const SAMPLE_RATE = 16000;

/** Whisper listens at 16 kHz mono PCM16, which is all this worklet produces. It sends
 *  40 ms at a time because the browser hands audio over in 8 ms slices, and five times
 *  the websocket frames buys nothing the server can act on.
 *  It lives in a blob because a worklet can only be loaded from a URL, and this much
 *  audio plumbing does not deserve its own entry in the build. */
const FRAME_SAMPLES = 640;
const WORKLET = `
class PcmWorklet extends AudioWorkletProcessor {
  frame = new Int16Array(${FRAME_SAMPLES});
  filled = 0;

  process(inputs) {
    const samples = inputs[0][0];
    if (!samples) return true;
    for (let i = 0; i < samples.length; i++) {
      this.frame[this.filled++] = Math.max(-1, Math.min(1, samples[i])) * 0x7fff;
      if (this.filled === this.frame.length) {
        this.port.postMessage(this.frame.buffer.slice(0));
        this.filled = 0;
      }
    }
    return true;
  }
}
registerProcessor("pcm", PcmWorklet);
`;

type Session = { socket: WebSocket; context: AudioContext; stream: MediaStream };

/** Streams the microphone to the server and reports each turn of speech the moment
 *  it is transcribed, while the microphone is still open. */
export function useAudioRecorder(onTranscript: (text: string) => void) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [microphoneIssue, setMicrophoneIssue] = useState<"unavailable" | null>(null);
  const [error, setError] = useState<unknown>(null);

  const session = useRef<Session | null>(null);

  function release() {
    const open = session.current;
    session.current = null;
    if (!open) return;
    open.stream.getTracks().forEach((track) => track.stop());
    void open.context.close();
    open.socket.close();
  }

  useEffect(() => () => release(), []);

  async function startRecording() {
    setMicrophoneIssue(null);
    setError(null);

    if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === "undefined") {
      setMicrophoneIssue("unavailable");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContext({ sampleRate: SAMPLE_RATE });
      await context.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET], { type: "text/javascript" })));

      const socket = new WebSocket(`${WS_URL}/api/transcriptions`);
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data);
        if (event.type === "transcript") onTranscript(event.text);
        else setError(new ApiError({ code: event.code, message: event.code }));
      };
      socket.onerror = () => setError(new ApiError({ code: "transcription_unavailable", message: "transcription_unavailable" }));
      // The server closes once it has sent the transcript of the final turn, so its
      // close is what ends the dictation: there is no other end-of-stream marker.
      socket.onclose = () => {
        setRecording(false);
        setTranscribing(false);
        release();
      };

      const microphone = new AudioWorkletNode(context, "pcm");
      microphone.port.onmessage = (message) => {
        if (socket.readyState === WebSocket.OPEN) socket.send(message.data);
      };
      // A worklet only runs inside a graph that reaches the destination, and the muted
      // gain is what keeps the speakers from playing the microphone back at the room.
      const muted = new GainNode(context, { gain: 0 });
      context.createMediaStreamSource(stream).connect(microphone).connect(muted).connect(context.destination);

      session.current = { socket, context, stream };
      setRecording(true);
    } catch {
      release();
      setMicrophoneIssue("unavailable");
    }
  }

  function stopRecording() {
    const open = session.current;
    if (!open) return;

    open.stream.getTracks().forEach((track) => track.stop());
    // An empty frame is "that was the last of the audio": the server transcribes what
    // is left and closes, which is what ends the dictation on this side.
    if (open.socket.readyState === WebSocket.OPEN) open.socket.send(new ArrayBuffer(0));
    setRecording(false);
    setTranscribing(true);
  }

  function toggleRecording() {
    if (recording) {
      stopRecording();
    } else {
      void startRecording();
    }
  }

  return {
    recording,
    transcribing,
    microphoneIssue,
    error,
    toggleRecording,
  };
}
