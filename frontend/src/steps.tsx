import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { api, type Progress } from "./api";
import type { ClaimDraft, Conflict, Resolution, SessionState } from "./types";
import { useDictation } from "./useDictation";
import { Button, Headline, Kicker, Lede, Problem, Tags } from "./ui";

interface StepProps {
  onDone: (state: SessionState) => void;
  onProgress: (event: Progress) => void;
  onRestart: () => void;
  setBusy: (busy: boolean) => void;
  busy: boolean;
}

/* One slide, one idea.
   The action bar sticks to the bottom of the stage. A slide can be taller than
   the viewport — five claims to review, three overlaps to settle — and the way
   forward must never be something you scroll to find. */
function Slide({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex min-h-full flex-col justify-center">
      <div className="pt-12 pb-6">{children}</div>
      {actions && (
        <div
          className="chrome sticky bottom-0 -mx-6 mt-auto flex flex-wrap items-center gap-3
                     bg-paper/80 px-6 py-4 backdrop-blur-xl"
        >
          {actions}
        </div>
      )}
    </div>
  );
}

const CARD = "rounded-2xl border border-line bg-surface transition-colors duration-[--state]";

/* ── 1. Capture ──────────────────────────────────────────────────────── */

export function CaptureStep({ onDone, onProgress, setBusy, busy }: StepProps) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [author, setAuthor] = useState(localStorage.getItem("ke.author") ?? "");
  const [error, setError] = useState<unknown>(null);

  // Segments land as the recogniser closes each phrase, so the transcript grows
  // while you are still talking rather than appearing all at once at the end.
  const { recording, error: micError, toggle } = useDictation((segment) =>
    setText((previous) => (previous ? `${previous} ${segment}` : segment)),
  );

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
    <Slide
      actions={
        <>
          <Button variant="primary" size="lg" onClick={submit} disabled={!text.trim() || busy}>
            {t("capture.submit")}
          </Button>
          <Button onClick={toggle} variant={recording ? "chosen" : "quiet"} size="lg">
            <span
              aria-hidden
              className={`h-2 w-2 rounded-full ${recording ? "bg-clay" : "bg-faint"}`}
              style={recording ? { animation: "breathe 1.2s ease-in-out infinite" } : undefined}
            />
            {recording ? t("capture.stop") : t("capture.record")}
          </Button>
          <input
            value={author}
            onChange={(event) => setAuthor(event.target.value)}
            placeholder={t("capture.name")}
            className="ml-auto w-40 rounded-full border border-line bg-surface px-4 py-2 text-sm
                       outline-none transition-colors duration-[--state] focus:border-verdigris"
          />
        </>
      }
    >
      <Kicker>{t("capture.eyebrow")}</Kicker>
      <Headline>{t("capture.title")}</Headline>
      <Lede>{t("capture.lead")}</Lede>

      <div className="relative mt-8">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={6}
          placeholder={t("capture.placeholder")}
          className={`${CARD} w-full resize-y p-5 text-[17px] leading-[1.6] shadow-card outline-none
                      placeholder:text-faint focus:border-verdigris
                      ${recording ? "border-verdigris" : ""}`}
        />
        {recording && (
          <span
            className="enter pointer-events-none absolute right-4 bottom-4 flex items-center gap-2
                       rounded-full bg-verdigris-soft px-2.5 py-1 font-mono text-[11px]
                       tracking-wider text-verdigris-ink uppercase"
          >
            <span
              aria-hidden
              className="h-1.5 w-1.5 rounded-full bg-clay"
              style={{ animation: "breathe 1.2s ease-in-out infinite" }}
            />
            {t("capture.listening")}
          </span>
        )}
      </div>
      <Problem error={error ?? micError} />
    </Slide>
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

  const edit = (id: string, patch: Partial<ClaimDraft>) =>
    setClaims((all) => all.map((claim) => (claim.id === id ? { ...claim, ...patch } : claim)));

  /* Grouped by the topic the model assigned. A flat list of eight claims is
     something you skim; the same eight under three headings is something you
     can check, because you see the shape of what it heard before reading a
     word of it. */
  const groups = useMemo(() => {
    const byTopic = new Map<string, ClaimDraft[]>();
    for (const claim of claims) {
      const topic = claim.topic?.trim() || t("confirm.untopiced");
      byTopic.set(topic, [...(byTopic.get(topic) ?? []), claim]);
    }
    return [...byTopic.entries()];
  }, [claims, t]);

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
    <Slide
      actions={
        <Button
          variant="primary"
          size="lg"
          onClick={() => send(false)}
          disabled={busy || claims.length === 0}
        >
          {t("confirm.submit")}
        </Button>
      }
    >
      <Kicker>{t("confirm.eyebrow")}</Kicker>
      <Headline>{t("confirm.title")}</Headline>
      {state.summary && <Lede>{state.summary}</Lede>}

      <div className="mt-9 space-y-8">
        {groups.map(([topic, group], groupIndex) => (
          <section key={topic}>
            <div className="mb-3 flex items-baseline gap-2.5">
              <h3 className="font-display text-[13px] font-semibold">{topic}</h3>
              <span className="font-mono text-[11px] text-faint">
                {t("confirm.count", { count: group.length })}
              </span>
              <span aria-hidden className="h-px flex-1 bg-line" />
            </div>
            <ul className="stagger space-y-2.5">
              {group.map((claim, index) => (
                <li
                  key={claim.id}
                  style={{ "--i": groupIndex * 2 + index } as React.CSSProperties}
                  className={`${CARD} group p-4 focus-within:border-verdigris hover:border-line-strong`}
                >
                  {/* The statement leads. It is the thing being checked, and
                      the topic is already the heading above — repeating it as a
                      card title was pure noise. The label only appears when it
                      says something the statement and the topic do not. */}
                  <div className="flex items-start gap-3">
                    <textarea
                      value={claim.statement}
                      onChange={(event) => edit(claim.id, { statement: event.target.value })}
                      aria-label={t("confirm.claim")}
                      rows={1}
                      className="autosize min-w-0 flex-1 resize-none bg-transparent text-[16px]
                                 leading-[1.6] outline-none"
                    />
                    <button
                      onClick={() => setClaims((all) => all.filter((c) => c.id !== claim.id))}
                      className="shrink-0 rounded-full px-2 text-[13px] text-faint opacity-0
                                 transition-[opacity,color] duration-[--press] hover:text-clay
                                 focus-visible:opacity-100 group-hover:opacity-100 max-sm:opacity-100"
                    >
                      {t("confirm.discard")}
                    </button>
                  </div>
                  {claim.title.trim().toLowerCase() !== topic.trim().toLowerCase() && (
                    <input
                      value={claim.title}
                      onChange={(event) => edit(claim.id, { title: event.target.value })}
                      aria-label={t("confirm.claimTitle")}
                      className="mt-1.5 w-full bg-transparent font-mono text-[11px] tracking-wider
                                 text-faint uppercase outline-none"
                    />
                  )}
                  <Tags tags={claim.tags} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {claims.length === 0 && (
        <p className="mt-8 rounded-2xl border border-dashed border-line p-8 text-[15px] text-muted">
          {t("confirm.empty")}
        </p>
      )}

      {state.open_questions.length > 0 && (
        <div className="enter mt-8 rounded-2xl bg-sunken p-5">
          <Kicker>{t("confirm.unclear", { count: state.open_questions.length })}</Kicker>
          <ul className="space-y-2 text-[16px]">
            {state.open_questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
          <textarea
            value={clarification}
            onChange={(event) => setClarification(event.target.value)}
            rows={1}
            placeholder={t("confirm.clarifyPlaceholder")}
            className="autosize mt-4 w-full resize-none rounded-xl border border-line bg-surface
                       p-3.5 text-[15px] outline-none transition-colors duration-[--state]
                       placeholder:text-faint focus:border-verdigris"
          />
          <Button
            className="mt-3"
            onClick={() => send(true)}
            disabled={!clarification.trim() || busy}
          >
            {t("confirm.reread")}
          </Button>
        </div>
      )}
      <Problem error={error} />
    </Slide>
  );
}

/* ── 3. Resolve overlaps ─────────────────────────────────────────────── */

function ConflictCard({
  conflict,
  incoming,
  resolution,
  onChange,
  index,
}: {
  conflict: Conflict;
  incoming: string;
  resolution: Resolution;
  onChange: (resolution: Resolution) => void;
  index: number;
}) {
  const { t } = useTranslation();
  const chosen = resolution.action;
  const merging = chosen === "merge";
  const recede = "transition-opacity duration-[--state] ease-[--ease-out]";

  return (
    <li style={{ "--i": index } as React.CSSProperties} className={`${CARD} overflow-hidden`}>
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 pt-4 pb-3">
        <span
          className={`rounded-full px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${
            conflict.verdict === "conflict" ? "bg-clay-soft text-clay" : "bg-sunken text-muted"
          }`}
        >
          {t(`conflicts.verdict.${conflict.verdict}`, conflict.verdict)}
        </span>
        <h3 className="font-display text-[15px] font-semibold tracking-[-0.01em]">
          {conflict.stored.title}
        </h3>
        <p className="text-[13px] text-muted">{conflict.reason}</p>
      </header>

      <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-2">
        <div
          className={`${recede} bg-stored p-5 ${chosen === "keep_new" || merging ? "opacity-30" : ""}`}
        >
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-faint">
            {t("conflicts.stored")}
          </p>
          <p className="font-mono text-[13px] leading-[1.65]">{conflict.stored.statement}</p>
        </div>
        <div className={`${recede} bg-incoming p-5 ${chosen === "keep_old" ? "opacity-30" : ""}`}>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-faint">
            {t("conflicts.yours")}
          </p>
          <p className="font-mono text-[13px] leading-[1.65]">{incoming}</p>
        </div>
      </div>

      {/* Only the resolutions that make sense for this verdict. Keeping both
          sides of a contradiction is not offered: retrieval would surface two
          incompatible claims and leave the model to pick one. */}
      <div className="flex flex-wrap gap-2 p-4">
        {conflict.allowed.map((action) => (
          <Button
            key={action}
            variant={chosen === action ? "chosen" : "quiet"}
            aria-pressed={chosen === action}
            onClick={() =>
              onChange({
                action,
                statement: action === "merge" ? (resolution.statement ?? incoming) : null,
              })
            }
          >
            {t(`conflicts.${action}`)}
          </Button>
        ))}
      </div>

      <div className="reveal" data-open={merging}>
        <div>
          <div className="border-t border-line px-5 py-4">
            <label className="mb-2 block font-mono text-[11px] uppercase tracking-wider text-faint">
              {t("conflicts.mergeLabel")}
            </label>
            <textarea
              value={resolution.statement ?? incoming}
              onChange={(event) => onChange({ action: "merge", statement: event.target.value })}
              rows={2}
              className="autosize w-full resize-none rounded-xl border border-line bg-sunken p-3.5
                         font-mono text-[13px] leading-[1.65] outline-none
                         transition-colors duration-[--state] focus:border-verdigris"
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
  const [error, setError] = useState<unknown>(null);
  const none = state.conflicts.length === 0;

  /* Every overlap starts on the recommendation its verdict carries, so the
     common case is read-and-continue rather than click-every-card. The human
     gate is still the Save button. */
  const [resolutions, setResolutions] = useState<Record<string, Resolution>>(() =>
    Object.fromEntries(
      state.conflicts.map((conflict) => [
        conflict.key,
        { action: conflict.recommended, statement: null },
      ]),
    ),
  );

  const changed = state.conflicts.filter(
    (conflict) => resolutions[conflict.key]?.action !== conflict.recommended,
  ).length;

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
    <Slide
      actions={
        <>
          <Button variant="primary" size="lg" onClick={submit} disabled={busy}>
            {t("conflicts.submit")}
          </Button>
          {changed > 0 && (
            <span className="text-sm text-muted">{t("conflicts.changed", { count: changed })}</span>
          )}
        </>
      }
    >
      <Kicker>{t("conflicts.eyebrow")}</Kicker>
      <Headline>
        {none ? t("conflicts.titleNone") : t("conflicts.title", { count: state.conflicts.length })}
      </Headline>
      <Lede>{none ? t("conflicts.leadNone") : t("conflicts.lead")}</Lede>

      <ul className="stagger mt-8 space-y-4">
        {state.conflicts.map((conflict, index) => (
          <ConflictCard
            key={conflict.key}
            index={index}
            conflict={conflict}
            incoming={state.claims.find((c) => c.id === conflict.draft_id)?.statement ?? ""}
            resolution={resolutions[conflict.key] ?? { action: conflict.recommended }}
            onChange={(resolution) =>
              setResolutions((previous) => ({ ...previous, [conflict.key]: resolution }))
            }
          />
        ))}
      </ul>
      <Problem error={error} />
    </Slide>
  );
}

/* ── 4. Saved ────────────────────────────────────────────────────────── */

export function DoneStep({ state, onRestart }: { state: SessionState; onRestart: () => void }) {
  const { t } = useTranslation();
  const none = state.committed.length === 0;

  return (
    <Slide
      actions={
        <Button variant="primary" size="lg" onClick={onRestart}>
          {t("done.restart")}
        </Button>
      }
    >
      <Kicker>{t("done.eyebrow")}</Kicker>
      <Headline>
        {none ? t("done.titleNone") : t("done.title", { count: state.committed.length })}
      </Headline>
      {!none && <Lede>{t("done.lead")}</Lede>}

      <ul className="stagger mt-8 space-y-3">
        {state.committed.map((claim, index) => (
          <li
            key={claim.id}
            style={{ "--i": index } as React.CSSProperties}
            className={`${CARD} p-5`}
          >
            <h3 className="font-display text-[15px] font-semibold tracking-[-0.01em]">
              {claim.title}
            </h3>
            <p className="mt-1.5 text-[16px] leading-[1.6]">{claim.statement}</p>
            {claim.superseded.length > 0 && (
              <p className="mt-3 font-mono text-[11px] text-faint">
                {t("done.replaced", { count: claim.superseded.length })}
              </p>
            )}
          </li>
        ))}
      </ul>
    </Slide>
  );
}
