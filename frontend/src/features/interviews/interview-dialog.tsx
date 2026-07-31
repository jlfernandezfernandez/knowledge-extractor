import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { AuthenticatedUser } from "@/features/auth/types";
import { ErrorNote } from "@/components/common/error-note";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { interviewsApi, type Interview } from "./api";

export function InterviewDialog({ onCreated }: { onCreated: (interview: Interview) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [assigneeId, setAssigneeId] = useState("");
  const [people, setPeople] = useState<AuthenticatedUser[]>([]);
  const [peopleLoading, setPeopleLoading] = useState(false);
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

  function personLabel(person: AuthenticatedUser) {
    return `${person.display_name} · ${person.email}`;
  }

  function changeOpen(nextOpen: boolean) {
    setOpen(nextOpen);
    if (!nextOpen) return;
    setPeopleLoading(true);
    setError(null);
    void interviewsApi.users()
      .then(setPeople)
      .catch(setError)
      .finally(() => setPeopleLoading(false));
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger render={<Button />}>{t("interviews.request")}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("interviews.dialog.title")}</DialogTitle>
          <DialogDescription>{t("interviews.dialog.description")}</DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={(event) => void submit(event)}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="assignee">{t("interviews.dialog.assignee")}</Label>
            <NativeSelect
              id="assignee"
              className="w-full"
              disabled={peopleLoading || people.length === 0}
              value={assigneeId}
              onChange={(event) => setAssigneeId(event.target.value)}
            >
              <NativeSelectOption value="">{peopleLoading ? t("interviews.dialog.loadingPeople") : t("interviews.dialog.assigneePlaceholder")}</NativeSelectOption>
              {people.map((person) => <NativeSelectOption key={person.id} value={person.id}>{personLabel(person)}</NativeSelectOption>)}
            </NativeSelect>
          </div>
          <div className="flex flex-col gap-2"><Label htmlFor="interview-title">{t("interviews.dialog.titleLabel")}</Label><Input id="interview-title" value={title} onChange={(event) => setTitle(event.target.value)} /></div>
          <div className="flex flex-col gap-2"><Label htmlFor="interview-brief">{t("interviews.dialog.brief")}</Label><Textarea id="interview-brief" value={brief} onChange={(event) => setBrief(event.target.value)} /></div>
          <ErrorNote error={error} />
          <DialogFooter><Button type="submit" disabled={busy || !assigneeId.trim() || !title.trim()}>{t("interviews.dialog.submit")}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
