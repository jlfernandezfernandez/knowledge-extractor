import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

// ponytail: child selectors instead of @tailwindcss/typography, one dependency less.
// Swap for `prose` classes if the answer ever needs full article styling.
const markdownStyles =
  "flex flex-col gap-3 leading-7 " +
  "[&_a]:underline [&_a]:underline-offset-4 " +
  "[&_strong]:font-semibold " +
  "[&_ul]:flex [&_ul]:list-disc [&_ul]:flex-col [&_ul]:gap-1 [&_ul]:ps-5 " +
  "[&_ol]:flex [&_ol]:list-decimal [&_ol]:flex-col [&_ol]:gap-1 [&_ol]:ps-5 " +
  "[&_h1]:text-base [&_h2]:text-base [&_h3]:text-sm [&_:is(h1,h2,h3)]:font-semibold " +
  "[&_blockquote]:border-s-2 [&_blockquote]:ps-3 [&_blockquote]:text-muted-foreground " +
  "[&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-sm " +
  "[&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 " +
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0 " +
  "[&_table]:w-full [&_table]:text-sm [&_:is(th,td)]:border-b [&_:is(th,td)]:px-2 [&_:is(th,td)]:py-1 [&_th]:text-start";

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn(markdownStyles, className)}>
      {/* Raw HTML stays disabled (react-markdown's default): answers come from a model. */}
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
