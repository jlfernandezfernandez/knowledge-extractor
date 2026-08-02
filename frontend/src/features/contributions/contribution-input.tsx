import { useState } from "react";
import { MicIcon, SquareIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ErrorNote } from "@/components/common/error-note";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";

type ContributionInputProps = {
  title?: string;
  subtitle?: string;
  placeholder?: string;
  textareaAriaLabel?: string;
  submitLabel?: string;
  busy?: boolean;
  onSubmit: (text: string) => Promise<void> | void;
  titleHeadingLevel?: "h1" | "h2";
  initialText?: string;
};

export function ContributionInput({
  title,
  subtitle,
  placeholder,
  textareaAriaLabel,
  submitLabel,
  busy = false,
  onSubmit,
  titleHeadingLevel = "h1",
  initialText = "",
}: ContributionInputProps) {
  const { t } = useTranslation();
  const [text, setText] = useState(initialText);

  const {
    recording,
    transcribing,
    microphoneIssue,
    error: recorderError,
    toggleRecording,
  } = useAudioRecorder((transcript) => {
    // One transcript per turn of speech, so each arrives as its own sentence.
    setText((current) => (current.trim() ? `${current.trim()} ${transcript}` : transcript));
  });

  const TitleTag = titleHeadingLevel;

  async function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || busy || transcribing) return;
    await onSubmit(trimmed);
  }

  return (
    <section aria-labelledby={title ? "contribution-input-heading" : undefined}>
      {title && (
        <TitleTag id="contribution-input-heading" className="text-2xl font-semibold">
          {title}
        </TitleTag>
      )}
      {subtitle && <p className="mt-2 text-muted-foreground">{subtitle}</p>}
      <Textarea
        aria-label={textareaAriaLabel || t("home.composerLabel")}
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="mt-6 min-h-36 resize-y"
        placeholder={placeholder || t("home.placeholder")}
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
          {transcribing ? (
            <Spinner data-icon="inline-start" />
          ) : recording ? (
            <SquareIcon data-icon="inline-start" />
          ) : (
            <MicIcon data-icon="inline-start" />
          )}
        </Button>
        <Button
          onClick={() => void handleSubmit()}
          disabled={busy || transcribing || !text.trim()}
        >
          {submitLabel || t("home.submit")}
        </Button>
      </div>
      {microphoneIssue && (
        <Alert className="mt-4" variant="destructive">
          <AlertTitle>{t("home.microphone.unavailable.title")}</AlertTitle>
          <AlertDescription>{t("home.microphone.unavailable.description")}</AlertDescription>
        </Alert>
      )}
      <ErrorNote error={recorderError} />
    </section>
  );
}
