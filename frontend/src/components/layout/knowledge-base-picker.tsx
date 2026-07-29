import { useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckIcon, ChevronsUpDownIcon, PlusIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { ErrorNote } from "@/components/common/error-note";
import type { KnowledgeBases } from "@/hooks/use-knowledge-bases";
import { cn } from "@/lib/utils";

/**
 * Which knowledge base you are feeding.
 *
 * It sits at the top of the rail because it is the widest-scoped thing on
 * screen: everything below and to the right happens inside whatever this says.
 * The claim count is on each row so an empty knowledge base is obvious before
 * you start talking into it.
 */
export function KnowledgeBasePicker({ bases }: { bases: KnowledgeBases }) {
  const { t } = useTranslation();
  const [creating, setCreating] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              className="h-9 w-full justify-start gap-2 px-2 text-[13px] font-medium"
            />
          }
        >
          <span className="truncate">{bases.current?.name ?? t("bases.none")}</span>
          <ChevronsUpDownIcon className="ml-auto shrink-0 text-muted-foreground" />
        </DropdownMenuTrigger>

        <DropdownMenuContent align="start" className="w-60">
          {bases.items.map((base) => (
            <DropdownMenuItem key={base.id} onClick={() => bases.select(base.slug)}>
              <CheckIcon
                className={cn("shrink-0", base.slug !== bases.slug && "opacity-0")}
                aria-hidden
              />
              <span className="truncate">{base.name}</span>
              <span className="ml-auto font-mono text-[11px] text-muted-foreground">
                {base.claims}
              </span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreating(true)}>
            <PlusIcon />
            {t("bases.create")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CreateKnowledgeBase
        open={creating}
        onClose={() => setCreating(false)}
        onCreate={bases.create}
      />
    </>
  );
}

function CreateKnowledgeBase({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string) => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await onCreate(name.trim());
      setName("");
      onClose();
    } catch (failed) {
      setError(failed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent showCloseButton={false} className="gap-4 p-5">
        <DialogTitle className="text-[15px] font-semibold">{t("bases.create")}</DialogTitle>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t("bases.namePlaceholder")}
            aria-label={t("bases.name")}
            className="h-10 w-full rounded-xl border border-input bg-transparent px-3 text-[15px]
                       outline-none transition-colors placeholder:text-muted-foreground
                       focus:border-foreground/25"
          />
          <p className="text-[13px] leading-relaxed text-muted-foreground">{t("bases.hint")}</p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("bases.cancel")}
            </Button>
            <Button type="submit" disabled={!name.trim() || busy}>
              {t("bases.confirm")}
            </Button>
          </div>
          <ErrorNote error={error} />
        </form>
      </DialogContent>
    </Dialog>
  );
}
