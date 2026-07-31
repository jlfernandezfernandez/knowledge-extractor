import { useEffect, useRef, useState } from "react";
import { contributionsApi } from "@/features/contributions/api";

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

  async function transcribeRecording() {
    const audio = new Blob(audioChunks.current, { type: "audio/webm" });
    if (!audio.size) return;
    setTranscribing(true);
    setError(null);
    try {
      const { text: transcript } = await contributionsApi.transcribe(audio);
      if (transcript) {
        onTranscribed(transcript);
      }
    } catch (failure) {
      setError(failure);
    } finally {
      setTranscribing(false);
    }
  }

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
      nextRecorder.ondataavailable = (event) => audioChunks.current.push(event.data);
      nextRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        void transcribeRecording();
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
