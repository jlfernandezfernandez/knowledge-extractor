import { useTranslation } from "react-i18next";
import { ArrowUpIcon, MicIcon, SquareIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  recording: boolean;
  onToggleRecording: () => void;
}

/**
 * Say it.
 *
 * One surface that lifts off the page, growing with what you type until it
 * would take over the screen. Enter sends and Shift+Enter breaks the line,
 * which is the contract every text box next to this one already has — the
 * hint under it says so once rather than being learned by accident.
 *
 * Dictation lives inside the composer rather than beside it, because it is
 * another way to fill this same box, not a separate mode.
 */
export function Composer({
  value,
  onChange,
  onSubmit,
  disabled,
  recording,
  onToggleRecording,
}: ComposerProps) {
  const { t } = useTranslation();
  const empty = !value.trim();

  return (
    <div className="mt-7">
      <div
        className={cn(
          "rounded-[26px] border bg-composer shadow-composer transition-colors duration-[--state]",
          recording ? "border-foreground/30" : "border-input focus-within:border-foreground/25",
        )}
      >
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!empty && !disabled) onSubmit();
            }
          }}
          rows={2}
          placeholder={t("capture.placeholder")}
          aria-label={t("capture.title")}
          className="autosize block max-h-[42vh] w-full resize-none overflow-y-auto bg-transparent
                     px-5 pt-4 pb-1 text-[16px] leading-relaxed outline-none
                     placeholder:text-muted-foreground"
        />

        <div className="flex items-center gap-2 px-3 pb-3">
          <Button
            type="button"
            variant={recording ? "default" : "ghost"}
            size="icon"
            className="rounded-full"
            aria-pressed={recording}
            aria-label={recording ? t("capture.stop") : t("capture.record")}
            onClick={onToggleRecording}
          >
            {recording ? <SquareIcon /> : <MicIcon />}
          </Button>

          {recording && (
            <span className="enter flex items-center gap-1.5 text-[13px] text-muted-foreground">
              <span aria-hidden className="breathe size-1.5 rounded-full bg-foreground" />
              {t("capture.listening")}
            </span>
          )}

          <Button
            type="button"
            size="icon"
            className="ml-auto rounded-full"
            onClick={onSubmit}
            disabled={empty || disabled}
            aria-label={t("capture.submit")}
          >
            <ArrowUpIcon />
          </Button>
        </div>
      </div>

      <p className="mt-2.5 px-1 text-center text-[12px] text-muted-foreground/80">
        {t("capture.keyHint")}
      </p>
    </div>
  );
}
