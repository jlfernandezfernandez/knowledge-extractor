import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { api, type Progress } from "./api";
import type { ClaimDraft, Conflict, Resolution, SessionState } from "./types";
import { Button, Eyebrow, Lead, Problem, Tags, Title } from "./ui";

interface StepProps {
  onDone: (state: SessionState) => void;
  onProgress: (event: Progress) => void;
  setBusy: (busy: boolean) => void;
  busy: boolean;
}

const CARD =
  "rounded-xl border border-line bg-surface shadow-card transition-colors duration-[--state]";
const FIELD =
  "w-full rounded-xl border border-line bg-surface p-4 text-[15px] leading-relaxed outline-none " +
  "transition-colors duration-[--state] placeholder:text-faint focus:border-verdigris";

/* ── 1. Capture ──────────────────────────────────────────────────────── */

export function CaptureStep({ onDone, onProgress, setBusy, busy }: StepProps) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [author, setAuthor] = useState(localStorage.getItem("ke.author") ?? "");
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const recorder = useRef<MediaRecorder | null>(null);

  async function toggleRecording() {
    if (recorder.current?.state === "recording") return recorder.current.stop();
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const rec = new MediaRecorder(mediaStream);
      rec.ondataavailable = (event) => chunks.push(event.data);
      rec.onstop = async () => {
        mediaStream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        try {
          const { text: spoken } = await api.transcribe(
            new Blob(chunks, { type: "audio/webm" }),
          );
          setText((previous) => `${previous}\n${spoken}`.trim());
        } catch (failure) {
          setError(failure);
        }
      };
      rec.start();
      recorder.current = rec;
      setRecording(true);
    } catch (failure) {
      setError(failure);
    }
  }

  async function submit() {
    setBusy(true);
    setError(null);
    localStorage.setItem("ke.author", author);
    try {
      onDone(await api.capture(text, author, onProgress));
    } catch (failure) {
      setError(failure);
      setBusy(false);
    }
  }

  return (
    <section className="enter">
      <Eyebrow>{t("capture.eyebrow")}</Eyebrow>
      <Title>{t("capture.title")}</Title>
      <Lead>{t("capture.lead")}</Lead>

      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={8}
        placeholder={t("capture.placeholder")}
        className={`${FIELD} mt-6 resize-y`}
      />

      <div className="mt-4 flex flex-wrap items-center gap-2.5">
        <input
          value={author}
          onChange={(event) => setAuthor(event.target.value)}
          placeholder={t("capture.name")}
          className="w-44 rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none
                     transition-colors duration-[--state] focus:border-verdigris"
        />
        <Button onClick={toggleRecording} variant={recording ? "chosen" : "quiet"}>
          <span
            aria-hidden
            className={`h-2 w-2 rounded-full ${recording ? "bg-clay" : "bg-faint"}`}
            style={recording ? { animation: "breathe 1.2s ease-in-out infinite" } : undefined}
          />
          {recording ? t("capture.stop") : t("capture.record")}
        </Button>
        <Button variant="primary" onClick={submit} disabled={!text.trim() || busy}>
          {t("capture.submit")}
        </Button>
      </div>
      <Problem error={error} />
    </section>
  );
}

/* ── 2. Confirm what was understood ──────────────────────────────────── */

export function ConfirmStep({
  state,
  onDone,
  onProgress,
  setBusy,
  busy,
}: StepProps & { state: SessionState }) {
  const { t } = useTranslation();
  const [claims, setClaims] = useState<ClaimDraft[]>(state.claims);
  const [clarification, setClarification] = useState("");
  const [error, setError] = useState<unknown>(null);

  const edit = (index: number, patch: Partial<ClaimDraft>) =>
    setClaims((all) => all.map((claim, i) => (i === index ? { ...claim, ...patch } : claim)));

  async function send(withClarification: boolean) {
    setBusy(true);
    setError(null);
    try {
      onDone(
        await api.confirm(
          state.session_id,
          claims,
          withClarification ? clarification : undefined,
          onProgress,
        ),
      );
      setClarification("");
    } catch (failure) {
      setError(failure);
      setBusy(false);
    }
  }

  return (
    <section className="enter">
      <Eyebrow>{t("confirm.eyebrow")}</Eyebrow>
      <Title>{t("confirm.title")}</Title>
      {state.summary && (
        <p className="mt-4 max-w-[58ch] border-l-2 border-verdigris pl-4 text-[15px] leading-relaxed">
          {state.summary}
        </p>
      )}

      <ul className="stagger mt-6 space-y-3">
        {claims.map((claim, index) => (
          <li
            key={claim.id}
            style={{ "--i": index } as React.CSSProperties}
            className={`${CARD} group p-4 focus-within:border-verdigris hover:border-line-strong`}
          >
            <div className="flex items-start gap-3">
              <input
                value={claim.title}
                onChange={(event) => edit(index, { title: event.target.value })}
                aria-label={t("confirm.claimTitle")}
                className="min-w-0 flex-1 bg-transparent font-display text-[15px] font-semibold outline-none"
              />
              <button
                onClick={() => setClaims((all) => all.filter((_, i) => i !== index))}
                className="shrink-0 rounded px-1.5 text-[13px] text-faint opacity-0 transition-[opacity,color]
                           duration-[--press] hover:text-clay focus-visible:opacity-100
                           group-hover:opacity-100 max-sm:opacity-100"
              >
                {t("confirm.discard")}
              </button>
            </div>
            <textarea
              value={claim.statement}
              onChange={(event) => edit(index, { statement: event.target.value })}
              aria-label={t("confirm.claim")}
              rows={1}
              className="autosize mt-1 w-full resize-none bg-transparent text-[15px] leading-relaxed outline-none"
            />
            <Tags tags={claim.tags} />
          </li>
        ))}
      </ul>

      {claims.length === 0 && (
        <p className="mt-6 rounded-xl border border-dashed border-line p-6 text-sm text-muted">
          {t("confirm.empty")}
        </p>
      )}

      {state.open_questions.length > 0 && (
        <div className="enter mt-8 rounded-xl bg-sunken p-4">
          <Eyebrow>{t("confirm.unclear")}</Eyebrow>
          <ul className="space-y-1.5 text-[15px]">
            {state.open_questions.map((question) => (
              <li key={question} className="flex gap-2.5">
                <span aria-hidden className="font-mono text-verdigris">
                  ?
                </span>
                {question}
              </li>
            ))}
          </ul>
          <textarea
            value={clarification}
            onChange={(event) => setClarification(event.target.value)}
            rows={2}
            placeholder={t("confirm.clarifyPlaceholder")}
            className={`${FIELD} autosize mt-3 resize-none p-3 text-sm`}
          />
          <Button className="mt-2.5" onClick={() => send(true)} disabled={!clarification.trim() || busy}>
            {t("confirm.reread")}
          </Button>
        </div>
      )}

      <div className="mt-8">
        <Button variant="primary" onClick={() => send(false)} disabled={busy}>
          {t("confirm.submit")}
        </Button>
      </div>
      <Problem error={error} />
    </section>
  );
}

/* ── 3. Resolve conflicts ────────────────────────────────────────────── */

const CHOICES: Resolution["action"][] = ["keep_new", "keep_old", "keep_both", "merge"];

function ConflictLedger({
  conflict,
  incoming,
  resolution,
  onChange,
  index,
}: {
  conflict: Conflict;
  incoming: string;
  resolution?: Resolution;
  onChange: (resolution: Resolution) => void;
  index: number;
}) {
  const { t } = useTranslation();
  const chosen = resolution?.action;
  const merging = chosen === "merge";
  // The losing side recedes rather than disappearing. Nothing is destroyed
  // here — a superseded claim is kept — and the layout should say so.
  const recede = "transition-opacity duration-[--state] ease-[--ease-out]";

  return (
    <li
      style={{ "--i": index } as React.CSSProperties}
      className={`${CARD} overflow-hidden`}
    >
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-line px-4 py-3">
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-wider ${
            conflict.verdict === "conflict"
              ? "bg-clay-soft text-clay"
              : "bg-sunken text-muted"
          }`}
        >
          {t(`conflicts.verdict.${conflict.verdict}`, conflict.verdict)}
        </span>
        <h3 className="font-display text-[15px] font-semibold">{conflict.stored.title}</h3>
        <p className="text-[13px] text-muted">{conflict.reason}</p>
      </header>

      <div className="grid grid-cols-1 divide-y divide-line sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <div
          className={`${recede} bg-stored p-4 ${chosen === "keep_new" || merging ? "opacity-35" : ""}`}
        >
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-faint">
            {t("conflicts.stored")}
          </p>
          <p className="font-mono text-[13px] leading-relaxed">{conflict.stored.statement}</p>
        </div>
        <div className={`${recede} bg-incoming p-4 ${chosen === "keep_old" ? "opacity-35" : ""}`}>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-faint">
            {t("conflicts.yours")}
          </p>
          <p className="font-mono text-[13px] leading-relaxed">{incoming}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-line px-4 py-3">
        {CHOICES.map((action) => (
          <Button
            key={action}
            variant={chosen === action ? "chosen" : "quiet"}
            aria-pressed={chosen === action}
            onClick={() =>
              onChange({
                action,
                statement: action === "merge" ? (resolution?.statement ?? incoming) : null,
              })
            }
          >
            {t(`conflicts.${action}`)}
          </Button>
        ))}
      </div>

      <div className="reveal" data-open={merging}>
        <div>
          <div className="border-t border-line px-4 py-3">
            <label className="mb-2 block font-mono text-[11px] uppercase tracking-wider text-faint">
              {t("conflicts.mergeLabel")}
            </label>
            <textarea
              value={resolution?.statement ?? incoming}
              onChange={(event) => onChange({ action: "merge", statement: event.target.value })}
              rows={3}
              className="w-full resize-none rounded-lg border border-line bg-sunken p-3 font-mono
                         text-[13px] leading-relaxed outline-none transition-colors
                         duration-[--state] focus:border-verdigris"
            />
          </div>
        </div>
      </div>
    </li>
  );
}

export function ConflictStep({
  state,
  onDone,
  setBusy,
  busy,
}: Omit<StepProps, "onProgress"> & { state: SessionState }) {
  const { t } = useTranslation();
  const [resolutions, setResolutions] = useState<Record<string, Resolution>>({});
  const [error, setError] = useState<unknown>(null);
  const undecided = state.conflicts.filter((conflict) => !resolutions[conflict.key]).length;
  const none = state.conflicts.length === 0;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const next = await api.resolve(state.session_id, resolutions);
      onDone(next);
      if (next.committed.length > 0) {
        toast.success(t("done.toast", { count: next.committed.length }));
      }
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="enter">
      <Eyebrow>{t("conflicts.eyebrow")}</Eyebrow>
      <Title>
        {none ? t("conflicts.titleNone") : t("conflicts.title", { count: state.conflicts.length })}
      </Title>
      <Lead>{none ? t("conflicts.leadNone") : t("conflicts.lead")}</Lead>

      <ul className="stagger mt-6 space-y-4">
        {state.conflicts.map((conflict, index) => (
          <ConflictLedger
            key={conflict.key}
            index={index}
            conflict={conflict}
            incoming={state.claims.find((c) => c.id === conflict.draft_id)?.statement ?? ""}
            resolution={resolutions[conflict.key]}
            onChange={(resolution) =>
              setResolutions((previous) => ({ ...previous, [conflict.key]: resolution }))
            }
          />
        ))}
      </ul>

      <div className="mt-8 flex items-center gap-3">
        <Button variant="primary" onClick={submit} disabled={busy || undecided > 0}>
          {t("conflicts.submit")}
        </Button>
        {undecided > 0 && (
          <span className="text-sm text-muted">{t("conflicts.undecided", { count: undecided })}</span>
        )}
      </div>
      <Problem error={error} />
    </section>
  );
}

/* ── 4. Committed ────────────────────────────────────────────────────── */

export function DoneStep({
  state,
  onRestart,
}: {
  state: SessionState;
  onRestart: () => void;
}) {
  const { t } = useTranslation();
  const none = state.committed.length === 0;

  return (
    <section className="enter">
      <Eyebrow>{t("done.eyebrow")}</Eyebrow>
      <Title>
        {none ? t("done.titleNone") : t("done.title", { count: state.committed.length })}
      </Title>

      <ul className="stagger mt-6 space-y-3">
        {state.committed.map((claim, index) => (
          <li
            key={claim.id}
            style={{ "--i": index } as React.CSSProperties}
            className={`${CARD} p-4`}
          >
            <h3 className="font-display text-[15px] font-semibold">{claim.title}</h3>
            <p className="mt-1 text-[15px] leading-relaxed">{claim.statement}</p>
            {claim.superseded.length > 0 && (
              <p className="mt-2 font-mono text-[11px] text-faint">
                {t("done.replaced", { count: claim.superseded.length })}
              </p>
            )}
          </li>
        ))}
      </ul>

      <Button variant="primary" className="mt-8" onClick={onRestart}>
        {t("done.restart")}
      </Button>
    </section>
  );
}
