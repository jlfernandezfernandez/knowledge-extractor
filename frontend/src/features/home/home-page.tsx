import { useEffect, useRef, useState } from "react";
import { MicIcon, SquareIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { contributionsApi } from "@/features/contributions/api";
import { interviewsApi, type Interview } from "@/features/interviews/api";

function PendingInterview({ interview, onStart }: { interview: Interview; onStart: (interview: Interview) => void }) {
  const { t } = useTranslation();
  return (
    <li className="flex items-center gap-3 border-b py-3 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{interview.title}</p>
        <p className="text-sm text-muted-foreground">{new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(interview.created_at))}</p>
      </div>
      <Badge variant="secondary">{t("interviews.status.pending")}</Badge>
      <Button size="sm" onClick={() => onStart(interview)}>{t("interviews.start")}</Button>
    </li>
  );
}

export function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [pending, setPending] = useState<Interview[]>([]);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [microphoneIssue, setMicrophoneIssue] = useState<"unavailable" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  useEffect(() => {
    void interviewsApi.list("pending").then(setPending).catch(setError);
  }, []);

  useEffect(() => () => recorder.current?.stream.getTracks().forEach((track) => track.stop()), []);

  async function createContribution() {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const contribution = await contributionsApi.create(text.trim());
      navigate(`/review/${contribution.id}`);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  async function startInterview(interview: Interview) {
    setBusy(true);
    setError(null);
    try {
      const started = await interviewsApi.start(interview.id);
      navigate(`/review/${started.contribution_id}`, { state: { interview: started.interview } });
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    setMicrophoneIssue(null);
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

  async function transcribeRecording() {
    const audio = new Blob(audioChunks.current, { type: "audio/webm" });
    if (!audio.size) return;
    setTranscribing(true);
    setError(null);
    try {
      const { text: transcript } = await contributionsApi.transcribe(audio);
      setText((current) => [current, transcript].filter(Boolean).join("\n\n"));
    } catch (failure) {
      setError(failure);
    } finally {
      setTranscribing(false);
    }
  }

  function toggleRecording() {
    if (recording) {
      recorder.current?.stop();
      return;
    }
    void startRecording();
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-3.5rem)] w-full max-w-3xl flex-col justify-center px-4 py-10">
      <section aria-labelledby="contribution-heading">
        <h1 id="contribution-heading" className="text-center text-2xl font-semibold">{t("home.title")}</h1>
        <p className="mt-2 text-center text-muted-foreground">{t("home.lead")}</p>
        <Textarea
          aria-label={t("home.composerLabel")}
          value={text}
          onChange={(event) => setText(event.target.value)}
          className="mt-6 min-h-36 resize-y"
          placeholder={t("home.placeholder")}
        />
        <div className="mt-3 flex items-center justify-between">
          <Button
            aria-label={t(recording ? "home.stopRecording" : "home.recordAudio")}
            disabled={busy || transcribing}
            onClick={toggleRecording}
            size="icon"
            type="button"
            variant={recording ? "destructive" : "ghost"}
          >
            {recording ? <SquareIcon data-icon="inline-start" /> : <MicIcon data-icon="inline-start" />}
          </Button>
          <Button onClick={() => void createContribution()} disabled={busy || transcribing || !text.trim()}>{t("home.submit")}</Button>
        </div>
        {microphoneIssue && (
          <Alert className="mt-4" variant="destructive">
            <AlertTitle>{t("home.microphone.unavailable.title")}</AlertTitle>
            <AlertDescription>{t("home.microphone.unavailable.description")}</AlertDescription>
          </Alert>
        )}
      </section>

      <section className="mt-12" aria-labelledby="pending-heading">
        <div className="flex items-center justify-between gap-4">
          <h2 id="pending-heading" className="font-medium">{t("home.pendingTitle")}</h2>
          <Link to="/interviews" className="text-sm font-medium text-primary underline-offset-4 hover:underline">{t("home.allInterviews")}</Link>
        </div>
        {pending.length ? <ul className="mt-2">{pending.slice(0, 3).map((item) => <PendingInterview key={item.id} interview={item} onStart={(item) => void startInterview(item)} />)}</ul> : <p className="mt-3 text-sm text-muted-foreground">{t("interviews.empty.pending")}</p>}
      </section>
      <ErrorNote error={error} />
    </div>
  );
}
