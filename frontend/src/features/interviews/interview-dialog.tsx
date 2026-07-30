import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ErrorNote } from "@/components/common/error-note";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { interviewsApi, type Interview } from "./api";

export function InterviewDialog({ onCreated }: { onCreated: (interview: Interview) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [assigneeId, setAssigneeId] = useState("");
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!assigneeId.trim() || !title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      onCreated(await interviewsApi.create({ assignee_id: assigneeId.trim(), title: title.trim(), brief: brief.trim() }));
      setOpen(false);
      setAssigneeId("");
      setTitle("");
      setBrief("");
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>{t("interviews.request")}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("interviews.dialog.title")}</DialogTitle>
          <DialogDescription>{t("interviews.dialog.description")}</DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={(event) => void submit(event)}>
          <div className="space-y-2"><Label htmlFor="assignee-id">{t("interviews.dialog.assigneeId")}</Label><Input id="assignee-id" value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)} /></div>
          <div className="space-y-2"><Label htmlFor="interview-title">{t("interviews.dialog.titleLabel")}</Label><Input id="interview-title" value={title} onChange={(event) => setTitle(event.target.value)} /></div>
          <div className="space-y-2"><Label htmlFor="interview-brief">{t("interviews.dialog.brief")}</Label><Textarea id="interview-brief" value={brief} onChange={(event) => setBrief(event.target.value)} /></div>
          <ErrorNote error={error} />
          <DialogFooter><Button type="submit" disabled={busy || !assigneeId.trim() || !title.trim()}>{t("interviews.dialog.submit")}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
