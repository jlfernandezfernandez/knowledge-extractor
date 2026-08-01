import { useEffect, useRef, useState } from "react";
import { contributionsApi } from "@/features/contributions/api";
import { ApiError } from "@/lib/api";

export function useAudioRecorder(onTranscribed: (text: string) => void) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [microphoneIssue, setMicrophoneIssue] = useState<"unavailable" | null>(null);
  const [error, setError] = useState<unknown>(null);

  const recorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startRecording() {
    setMicrophoneIssue(null);
    setError(null);

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setMicrophoneIssue("unavailable");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const nextRecorder = new MediaRecorder(stream);
      audioChunks.current = [];

      nextRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.current.push(event.data);
      };

      nextRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        const audio = new Blob(audioChunks.current, { type: "audio/webm" });
        if (!audio.size) return;
        setTranscribing(true);
        try {
          await contributionsApi.transcribe(audio, (event) => {
            // The stream answers 200 even when it fails, so its error event is the failure.
            if (event.type === "delta") onTranscribed(event.text);
            else setError(new ApiError({ code: event.code, message: event.code }));
          });
        } catch (failure) {
          setError(failure);
        } finally {
          setTranscribing(false);
        }
      };

      nextRecorder.start();
      recorder.current = nextRecorder;
      setRecording(true);
    } catch {
      setMicrophoneIssue("unavailable");
    }
  }

  function stopRecording() {
    if (recorder.current && recorder.current.state !== "inactive") {
      recorder.current.stop();
    }
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
