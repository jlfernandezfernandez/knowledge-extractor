import { useTranslation } from "react-i18next";
import { useDictation } from "@/hooks/use-dictation";
import { ErrorNote } from "@/components/common/error-note";
import { Composer } from "./composer";

interface CaptureStepProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  busy: boolean;
}

/**
 * Step 1, and the only one that does not look like a step.
 *
 * It is a greeting and a box, centred in the stage: nothing has started yet,
 * so there is nothing to review, no progress to show and no reason to make it
 * feel like a form.
 */
export function CaptureStep({ value, onChange, onSubmit, busy }: CaptureStepProps) {
  const { t } = useTranslation();

  // Segments land as the recogniser closes each phrase, so the transcript
  // grows while you are still talking rather than appearing all at once.
  const { recording, error, toggle } = useDictation((segment) =>
    onChange(value ? `${value} ${segment}` : segment),
  );

  return (
    <div className="flex min-h-full flex-col justify-center pb-10">
      <h1 className="text-center text-[clamp(1.75rem,4vw,2.125rem)] leading-tight font-semibold tracking-[-0.025em] text-balance">
        {t("capture.title")}
      </h1>
      <p className="mx-auto mt-3 max-w-[52ch] text-center text-[15px] leading-relaxed text-muted-foreground text-pretty">
        {t("capture.lead")}
      </p>

      <Composer
        value={value}
        onChange={onChange}
        onSubmit={onSubmit}
        disabled={busy}
        recording={recording}
        onToggleRecording={toggle}
      />

      <ErrorNote error={error} />
    </div>
  );
}
