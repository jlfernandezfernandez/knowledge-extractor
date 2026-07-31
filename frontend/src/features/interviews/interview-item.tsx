import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Item, ItemActions, ItemContent, ItemDescription, ItemTitle } from "@/components/ui/item";
import { cn } from "@/lib/utils";
import type { Interview } from "./api";

/** One interview row. Given `onOpen` the whole row is the control: only interviews
 *  assigned to the reader can be opened, the rest are read-only. */
export function InterviewItem({
  interview,
  onOpen,
}: {
  interview: Interview;
  onOpen?: (interview: Interview) => void;
}) {
  const { t, i18n } = useTranslation();
  // The app's language, not the browser's: otherwise a Spanish UI on an English
  // system dates history one way and interviews the other.
  const date = new Intl.DateTimeFormat(i18n.resolvedLanguage ?? i18n.language, {
    dateStyle: "medium",
  }).format(new Date(interview.created_at));

  return (
    <Item
      className={cn(onOpen && "text-start hover:bg-muted")}
      render={onOpen ? <button type="button" onClick={() => onOpen(interview)} /> : undefined}
    >
      <ItemContent>
        <ItemTitle>{interview.title}</ItemTitle>
        <ItemDescription>{date}</ItemDescription>
      </ItemContent>
      <ItemActions>
        <Badge variant="secondary">{t(`interviews.status.${interview.status}`)}</Badge>
      </ItemActions>
    </Item>
  );
}
