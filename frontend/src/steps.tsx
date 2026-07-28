import { useRef, useState } from "react";
import { api } from "./api";
import type { ClaimDraft, Conflict, Resolution, SessionState } from "./types";
import { Button, Eyebrow, Problem, Tags, Title } from "./ui";

/* ---------- 1. Capture ---------- */

export function CaptureStep({
  onDone,
  busy,
  setBusy,
}: {
  onDone: (s: SessionState) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [author, setAuthor] = useState(localStorage.getItem("ke.author") ?? "");
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const recorder = useRef<MediaRecorder | null>(null);

  async function toggleRecording() {
    if (recorder.current?.state === "recording") {
      recorder.current.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        setBusy(true);
        try {
          const { text: spoken } = await api.transcribe(
            new Blob(chunks, { type: "audio/webm" }),
          );
          setText((prev) => `${prev}\n${spoken}`.trim());
        } catch (e) {
          setError(e);
        } finally {
          setBusy(false);
        }
      };
      rec.start();
      recorder.current = rec;
      setRecording(true);
    } catch (e) {
      setError(e);
    }
  }

  async function submit() {
    setBusy(true);
    setError(null);
    localStorage.setItem("ke.author", author);
    try {
      onDone(await api.capture(text, author));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="settle">
      <Eyebrow>Step one</Eyebrow>
      <Title>Say what you know</Title>
      <p className="mt-2 max-w-prose text-sm text-muted">
        Ramble. Half-finished thoughts are fine — the point of the next screen is to
        show you what was understood before any of it is stored.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={9}
        placeholder="The staging deploy moved to Fridays because Monday releases kept colliding with the sprint review…"
        className="mt-6 w-full resize-y rounded-xl border border-line bg-surface p-4 text-[15px]
                   leading-relaxed outline-none placeholder:text-muted/70 focus:border-verdigris"
      />

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="Your name"
          className="w-44 rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-verdigris"
        />
        <Button onClick={toggleRecording} variant={recording ? "chosen" : "quiet"}>
          <span
            className={`h-2 w-2 rounded-full ${recording ? "bg-clay" : "bg-muted"}`}
            aria-hidden
          />
          {recording ? "Stop recording" : "Record instead"}
        </Button>
        <Button variant="primary" onClick={submit} disabled={!text.trim() || busy}>
          Read it back to me
        </Button>
      </div>
      <Problem error={error} />
    </section>
  );
}

/* ---------- 2. Confirm what was understood ---------- */

export function ConfirmStep({
  state,
  onDone,
  busy,
  setBusy,
}: {
  state: SessionState;
  onDone: (s: SessionState) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
}) {
  const [claims, setClaims] = useState<ClaimDraft[]>(state.claims);
  const [clarification, setClarification] = useState("");
  const [error, setError] = useState<unknown>(null);

  function edit(index: number, patch: Partial<ClaimDraft>) {
    setClaims((cs) => cs.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  async function send(withClarification: boolean) {
    setBusy(true);
    setError(null);
    try {
      onDone(
        await api.confirm(
          state.session_id,
          claims,
          withClarification ? clarification : undefined,
        ),
      );
      setClarification("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="settle">
      <Eyebrow>Step two</Eyebrow>
      <Title>Here is what I understood</Title>
      {state.summary && (
        <p className="mt-3 max-w-prose border-l-2 border-verdigris pl-4 text-[15px] leading-relaxed">
          {state.summary}
        </p>
      )}

      <ul className="mt-6 space-y-3">
        {claims.map((claim, index) => (
          <li
            key={claim.id}
            className="group rounded-xl border border-line bg-surface p-4 transition-colors focus-within:border-verdigris"
          >
            <div className="flex items-start gap-3">
              <input
                value={claim.title}
                onChange={(e) => edit(index, { title: e.target.value })}
                aria-label="Claim title"
                className="flex-1 bg-transparent font-display text-base font-semibold outline-none"
              />
              <button
                onClick={() => setClaims((cs) => cs.filter((_, i) => i !== index))}
                aria-label={`Discard "${claim.title}"`}
                className="rounded px-2 text-muted opacity-0 transition-opacity hover:text-clay
                           group-hover:opacity-100 focus-visible:opacity-100"
              >
                Discard
              </button>
            </div>
            <textarea
              value={claim.statement}
              onChange={(e) => edit(index, { statement: e.target.value })}
              aria-label="Claim"
              rows={2}
              className="mt-1 w-full resize-none bg-transparent text-[15px] leading-relaxed outline-none"
            />
            <Tags tags={claim.tags} />
          </li>
        ))}
      </ul>

      {claims.length === 0 && (
        <p className="mt-6 rounded-xl border border-dashed border-line p-6 text-sm text-muted">
          Nothing left to store. Go back and add more, or discard this capture.
        </p>
      )}

      {state.open_questions.length > 0 && (
        <div className="mt-8 rounded-xl bg-sunken p-4">
          <Eyebrow>Still unclear</Eyebrow>
          <ul className="space-y-1 text-sm">
            {state.open_questions.map((q) => (
              <li key={q} className="flex gap-2">
                <span aria-hidden className="text-verdigris">
                  ?
                </span>
                {q}
              </li>
            ))}
          </ul>
          <textarea
            value={clarification}
            onChange={(e) => setClarification(e.target.value)}
            rows={2}
            placeholder="Answer here and I will re-read the whole thing…"
            className="mt-3 w-full resize-none rounded-lg border border-line bg-surface p-3 text-sm outline-none focus:border-verdigris"
          />
          <Button
            className="mt-2"
            onClick={() => send(true)}
            disabled={!clarification.trim() || busy}
          >
            Re-read with this
          </Button>
        </div>
      )}

      <div className="mt-8">
        <Button variant="primary" onClick={() => send(false)} disabled={busy}>
          That's right — check it against what we know
        </Button>
      </div>
      <Problem error={error} />
    </section>
  );
}

/* ---------- 3. Resolve conflicts ---------- */

const CHOICES: { action: Resolution["action"]; label: string }[] = [
  { action: "keep_new", label: "Take mine" },
  { action: "keep_old", label: "Keep stored" },
  { action: "keep_both", label: "Keep both" },
  { action: "merge", label: "Merge" },
];

const VERDICT_COPY: Record<string, string> = {
  conflict: "These disagree",
  duplicate: "Already stored",
  refines: "Adds detail",
};

function ConflictLedger({
  conflict,
  incoming,
  resolution,
  onChange,
}: {
  conflict: Conflict;
  incoming: string;
  resolution?: Resolution;
  onChange: (r: Resolution) => void;
}) {
  const chosen = resolution?.action;
  const dimStored = chosen === "keep_new" || chosen === "merge";
  const dimIncoming = chosen === "keep_old";

  return (
    <li className="settle overflow-hidden rounded-xl border border-line bg-surface">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-line px-4 py-3">
        <span
          className={
            "rounded px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-wider " +
            (conflict.verdict === "conflict"
              ? "bg-clay-soft text-clay"
              : "bg-sunken text-muted")
          }
        >
          {VERDICT_COPY[conflict.verdict] ?? conflict.verdict}
        </span>
        <h3 className="font-display text-[15px] font-semibold">{conflict.stored.title}</h3>
        <p className="text-sm text-muted">{conflict.reason}</p>
      </header>

      {/* The ledger: stored on the left, incoming on the right, a seam between
          them. Choosing a side recedes the other rather than deleting it —
          nothing is destroyed here, and the layout says so. */}
      <div className="grid grid-cols-1 divide-y divide-line sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <div
          className={`bg-stored p-4 transition-opacity ${dimStored ? "opacity-40" : ""}`}
        >
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-muted">
            Stored
          </p>
          <p className="font-mono text-[13px] leading-relaxed">
            {conflict.stored.statement}
          </p>
        </div>
        <div
          className={`bg-incoming p-4 transition-opacity ${dimIncoming ? "opacity-40" : ""}`}
        >
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-muted">
            Yours
          </p>
          <p className="font-mono text-[13px] leading-relaxed">{incoming}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-line px-4 py-3">
        {CHOICES.map(({ action, label }) => (
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
            {label}
          </Button>
        ))}
      </div>

      {chosen === "merge" && (
        <div className="settle border-t border-line px-4 py-3">
          <label className="mb-2 block font-mono text-[11px] uppercase tracking-wider text-muted">
            The claim that replaces both
          </label>
          <textarea
            value={resolution?.statement ?? incoming}
            onChange={(e) => onChange({ action: "merge", statement: e.target.value })}
            rows={3}
            className="w-full resize-none rounded-lg border border-line bg-sunken p-3 font-mono text-[13px] leading-relaxed outline-none focus:border-verdigris"
          />
        </div>
      )}
    </li>
  );
}

export function ConflictStep({
  state,
  onDone,
  busy,
  setBusy,
}: {
  state: SessionState;
  onDone: (s: SessionState) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
}) {
  const [resolutions, setResolutions] = useState<Record<string, Resolution>>({});
  const [error, setError] = useState<unknown>(null);
  const undecided = state.conflicts.filter((c) => !resolutions[c.key]).length;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      onDone(await api.resolve(state.session_id, resolutions));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const statementOf = (draftId: string) =>
    state.claims.find((c) => c.id === draftId)?.statement ?? "";

  return (
    <section className="settle">
      <Eyebrow>Step three</Eyebrow>
      <Title>
        {state.conflicts.length === 0
          ? "Nothing collides"
          : `${state.conflicts.length} thing${state.conflicts.length > 1 ? "s" : ""} to decide`}
      </Title>
      <p className="mt-2 max-w-prose text-sm text-muted">
        {state.conflicts.length === 0
          ? "None of this contradicts what is already stored. It can go straight in."
          : "You are the tie-breaker. Whichever side loses is kept and marked as superseded — the history stays."}
      </p>

      <ul className="mt-6 space-y-4">
        {state.conflicts.map((conflict) => (
          <ConflictLedger
            key={conflict.key}
            conflict={conflict}
            incoming={statementOf(conflict.draft_id)}
            resolution={resolutions[conflict.key]}
            onChange={(r) => setResolutions((prev) => ({ ...prev, [conflict.key]: r }))}
          />
        ))}
      </ul>

      <div className="mt-8 flex items-center gap-3">
        <Button variant="primary" onClick={submit} disabled={busy || undecided > 0}>
          Commit to the knowledge base
        </Button>
        {undecided > 0 && (
          <span className="text-sm text-muted">{undecided} still undecided</span>
        )}
      </div>
      <Problem error={error} />
    </section>
  );
}

/* ---------- 4. Committed ---------- */

export function DoneStep({
  state,
  onRestart,
}: {
  state: SessionState;
  onRestart: () => void;
}) {
  return (
    <section className="settle">
      <Eyebrow>Committed</Eyebrow>
      <Title>
        {state.committed.length === 0
          ? "Nothing new to store"
          : `${state.committed.length} claim${state.committed.length > 1 ? "s" : ""} indexed`}
      </Title>

      <ul className="mt-6 space-y-3">
        {state.committed.map((claim) => (
          <li key={claim.id} className="rounded-xl border border-line bg-surface p-4">
            <h3 className="font-display text-base font-semibold">{claim.title}</h3>
            <p className="mt-1 text-[15px] leading-relaxed">{claim.statement}</p>
            {claim.superseded.length > 0 && (
              <p className="mt-2 font-mono text-[11px] text-muted">
                replaced {claim.superseded.length} stored claim
                {claim.superseded.length > 1 ? "s" : ""}
              </p>
            )}
          </li>
        ))}
      </ul>

      <Button variant="primary" className="mt-8" onClick={onRestart}>
        Capture something else
      </Button>
    </section>
  );
}
