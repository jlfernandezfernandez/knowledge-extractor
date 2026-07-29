import { useEffect, useRef, useState } from "react";
import { Toaster } from "@/components/ui/sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { AskDialog } from "@/components/ask/ask-dialog";
import { ReviewFlow } from "@/components/review/review-flow";
import { useAuthor } from "@/hooks/use-author";
import { useHotkey } from "@/hooks/use-hotkey";
import { useKnowledgeBases } from "@/hooks/use-knowledge-bases";
import { useReview } from "@/hooks/use-review";

/**
 * Two panes: what you are feeding and what you have fed it on the left, the
 * review itself on the right.
 *
 * The stage is the only thing that scrolls, and the only thing that carries a
 * `view-transition-name` — the rail and the bar stay put while a step slides,
 * which is what keeps the app from feeling like it reloads on every click.
 */
export default function App() {
  const review = useReview();
  const bases = useKnowledgeBases();
  const [author, setAuthor] = useAuthor();
  const [asking, setAsking] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);

  // ⌘K, the shortcut every tool this sits next to already uses.
  useHotkey("k", () => setAsking((open) => !open));

  // A new step starts at the top of itself, not where the last one was read to.
  useEffect(() => {
    stageRef.current?.scrollTo({ top: 0 });
  }, [review.stage]);

  const closeMenu = () => setMenuOpen(false);
  const ask = () => {
    setAsking(true);
    closeMenu();
  };

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar
        bases={bases}
        // The rail lists sessions, so it goes stale the moment a review moves.
        version={review.version}
        activeSessionId={review.session?.session_id}
        onOpenSession={(id) => {
          review.resume(id);
          closeMenu();
        }}
        author={author}
        onAuthorChange={setAuthor}
        onNewCapture={() => {
          review.reset();
          closeMenu();
        }}
        onAsk={ask}
        open={menuOpen}
        onClose={closeMenu}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          stage={review.stage}
          canGoBack={review.canGoBack}
          onBack={review.back}
          onAsk={ask}
          onOpenMenu={() => setMenuOpen(true)}
        />
        <main
          ref={stageRef}
          className="min-h-0 flex-1 overflow-y-auto"
          style={{ viewTransitionName: "step" }}
        >
          <div className="mx-auto h-full max-w-3xl px-4 sm:px-6">
            <ReviewFlow
              review={review}
              author={author}
              knowledgeBase={bases.slug}
              // A commit changes the claim count the picker shows.
              onCommitted={bases.refresh}
            />
          </div>
        </main>
      </div>

      <AskDialog
        open={asking}
        onClose={() => setAsking(false)}
        knowledgeBase={bases.slug}
        knowledgeBaseName={bases.current?.name ?? ""}
      />
      <Toaster position="bottom-right" />
    </div>
  );
}
