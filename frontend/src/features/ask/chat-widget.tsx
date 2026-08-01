import { useEffect, useRef, useState } from "react";
import {
  ArrowUpIcon,
  CheckIcon,
  RotateCwIcon,
  SquareIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { Markdown } from "@/components/ui/markdown";
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker";
import { Message, MessageContent } from "@/components/ui/message";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { askStream, type AskEvent, type ClaimItem } from "./api";

type ToolRun = { name: string; done: boolean };

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  tools: ToolRun[];
  claims?: ClaimItem[];
};

function ChatTurn({ message }: { message: ChatMessage }) {
  const { t } = useTranslation();

  return (
    <Message align={message.role === "user" ? "end" : "start"}>
      <MessageContent>
        {message.tools.map((run) => (
          <Marker key={run.name} role={run.done ? undefined : "status"}>
            <MarkerIcon>{run.done ? <CheckIcon /> : <Spinner />}</MarkerIcon>
            <MarkerContent className={run.done ? undefined : "shimmer"}>
              {t(`ask.tools.${run.name}.${run.done ? "done" : "running"}`, {
                defaultValue: run.name,
              })}
            </MarkerContent>
          </Marker>
        ))}
        {message.text && (
          <Bubble variant={message.role === "user" ? "default" : "muted"}>
            <BubbleContent>
              {message.role === "user" ? (
                <span className="whitespace-pre-wrap">{message.text}</span>
              ) : (
                <Markdown>{message.text}</Markdown>
              )}
            </BubbleContent>
          </Bubble>
        )}
        {message.claims && message.claims.length > 0 && (
          <details className="mt-1.5 text-xs text-muted-foreground cursor-pointer select-none">
            <summary className="font-medium hover:underline">
              {t("ask.sources", { count: message.claims.length, defaultValue: `${message.claims.length} fuentes` })}
            </summary>
            <ul className="mt-1 space-y-1 pl-2 border-l border-zinc-200 dark:border-zinc-700">
              {message.claims.map((claim) => (
                <li key={claim.id} className="line-clamp-2">
                  <span className="font-semibold text-foreground">{claim.title}:</span> {claim.statement}
                </li>
              ))}
            </ul>
          </details>
        )}
      </MessageContent>
    </Message>
  );
}

export function ChatWidget() {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const threadId = useRef(crypto.randomUUID());
  // A ref, not `busy`: onerror also fires when a finished stream closes, and reading
  // state inside a state updater to tell the two apart double-fires under StrictMode.
  const streaming = useRef(false);
  const source = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      source.current?.close();
    };
  }, []);

  function updateAnswer(update: (message: ChatMessage) => ChatMessage) {
    setMessages((current) =>
      current.map((message, index) =>
        index === current.length - 1 ? update(message) : message,
      ),
    );
  }

  // A turn that ended before it said anything leaves a blank gap where a bubble
  // should be, which reads as a rendering bug rather than as a stop or a failure.
  function dropSilentAnswer() {
    setMessages((current) => {
      const last = current[current.length - 1];
      const silent =
        last?.role === "assistant" && !last.text && !last.tools.length;
      return silent ? current.slice(0, -1) : current;
    });
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const asked = question.trim();
    if (!asked || busy) return;

    setQuestion("");
    setBusy(true);
    streaming.current = true;
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: asked, tools: [] },
      { id: crypto.randomUUID(), role: "assistant", text: "", tools: [] },
    ]);

    const stream = askStream(asked, threadId.current);
    source.current = stream;
    stream.onmessage = (event) => {
      let payload: AskEvent;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      if (payload.type === "claims") {
        updateAnswer((message) => ({
          ...message,
          claims: payload.items,
        }));
        return;
      }
      if (payload.type === "token") {
        updateAnswer((message) => ({
          ...message,
          text: message.text + payload.content,
        }));
        return;
      }
      if (payload.type === "tool") {
        updateAnswer((message) => ({
          ...message,
          tools: message.tools.some((run) => run.name === payload.name)
            ? message.tools.map((run) =>
                run.name === payload.name
                  ? { ...run, done: payload.done }
                  : run,
              )
            : [...message.tools, { name: payload.name, done: payload.done }],
        }));
        return;
      }
      if (payload.type === "error") {
        toast.add({
          type: "error",
          title: t("ask.failed"),
          description: t(`errors.${payload.code}`, {
            defaultValue: t("errors.requestFailed"),
          }),
        });
      }
      close();
    };
    stream.onerror = () => {
      // The browser also fires onerror when the server closes a finished stream, so
      // only a stream that was still running counts as a failure worth a toast.
      if (streaming.current)
        toast.add({ type: "error", title: t("ask.failed") });
      close();
    };

    function close() {
      streaming.current = false;
      stream.close();
      source.current = null;
      setBusy(false);
      dropSilentAnswer();
    }
  }

  function stop() {
    streaming.current = false;
    source.current?.close();
    source.current = null;
    setBusy(false);
    dropSilentAnswer();
  }

  function reset() {
    threadId.current = crypto.randomUUID();
    setMessages([]);
  }

  // Nothing to show yet for this turn: no token, no tool running.
  const pending = messages[messages.length - 1];
  const waiting =
    busy &&
    pending?.role === "assistant" &&
    !pending.text &&
    !pending.tools.length;

  return (
    <Popover>
      <PopoverTrigger
        render={
          <Button
            aria-label={t("ask.open")}
            className="fixed end-6 bottom-6 z-40 size-12 rounded-full shadow-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/80 dark:border-zinc-700/80 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-foreground"
            size="icon"
          >
            <span aria-hidden="true" className="text-xl leading-none select-none">🦉</span>
          </Button>
        }
      />
      <PopoverContent
        align="end"
        side="top"
        className="w-[min(24rem,calc(100vw-3rem))] p-0"
      >
        <Card className="h-[min(35rem,calc(100dvh-8rem))] gap-0 border-0 shadow-none">
          <CardHeader className="gap-1 border-b">
            <CardTitle>{t("ask.title")}</CardTitle>
            <CardDescription>{t("ask.lead")}</CardDescription>
            <CardAction>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      aria-label={t("ask.reset")}
                      disabled={busy || !messages.length}
                      onClick={reset}
                      size="icon"
                      variant="outline"
                    >
                      <RotateCwIcon />
                    </Button>
                  }
                />
                <TooltipContent>{t("ask.reset")}</TooltipContent>
              </Tooltip>
            </CardAction>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 overflow-hidden p-0">
            {messages.length === 0 ? (
              <Empty className="h-full">
                <EmptyHeader>
                  <EmptyMedia variant="icon" className="bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/60 shadow-2xs select-none">
                    <span aria-hidden="true" className="text-2xl leading-none">🦉</span>
                  </EmptyMedia>
                  <EmptyTitle>{t("ask.emptyTitle")}</EmptyTitle>
                  <EmptyDescription>{t("ask.emptyLead")}</EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              // Closing the popover unmounts the viewport, so every reopen is a
              // restore: land on the last question asked, not at the raw bottom.
              <MessageScrollerProvider autoScroll defaultScrollPosition="last-anchor">
                <MessageScroller>
                  <MessageScrollerViewport>
                    <MessageScrollerContent
                      aria-busy={busy}
                      className="p-(--card-spacing)"
                    >
                      {messages.map((message) => (
                        <MessageScrollerItem
                          key={message.id}
                          messageId={message.id}
                          scrollAnchor={message.role === "user"}
                        >
                          <ChatTurn message={message} />
                        </MessageScrollerItem>
                      ))}
                      {waiting && (
                        <MessageScrollerItem scrollAnchor={false}>
                          <Marker role="status">
                            <MarkerIcon>
                              <Spinner />
                            </MarkerIcon>
                            <MarkerContent className="shimmer">
                              {t("ask.thinking")}
                            </MarkerContent>
                          </Marker>
                        </MessageScrollerItem>
                      )}
                    </MessageScrollerContent>
                  </MessageScrollerViewport>
                  <MessageScrollerButton />
                </MessageScroller>
              </MessageScrollerProvider>
            )}
          </CardContent>
          <CardFooter>
            <form className="w-full" onSubmit={submit}>
              <InputGroup>
                <InputGroupTextarea
                  aria-label={t("ask.question")}
                  className="h-10 min-h-10 overflow-y-auto"
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  placeholder={t("ask.placeholder")}
                  value={question}
                />
                <InputGroupAddon align="block-end" className="p-2">
                  {busy ? (
                    <InputGroupButton
                      aria-label={t("ask.stop")}
                      className="ml-auto"
                      onClick={stop}
                      size="icon-sm"
                      type="button"
                      variant="default"
                    >
                      <SquareIcon className="fill-current" />
                    </InputGroupButton>
                  ) : (
                    <InputGroupButton
                      aria-label={t("ask.submit")}
                      className="ml-auto"
                      disabled={!question.trim()}
                      size="icon-sm"
                      type="submit"
                      variant="default"
                    >
                      <ArrowUpIcon />
                    </InputGroupButton>
                  )}
                </InputGroupAddon>
              </InputGroup>
            </form>
          </CardFooter>
        </Card>
      </PopoverContent>
    </Popover>
  );
}
