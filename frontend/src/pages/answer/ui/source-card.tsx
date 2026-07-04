import type { AnswerSource } from "@/entities/query";
import { Card, CardContent } from "@/shared/ui";

type Props = {
  source: AnswerSource;
};

/** Compact citation card matching the design reference. */
export function SourceCard({ source }: Props) {
  return (
    <Card className="rounded-[14px] border border-[hsl(var(--source-border))] bg-card shadow-none">
      <CardContent className="flex flex-col gap-1 p-4">
        <div className="text-[15px] font-semibold leading-snug text-foreground">
          {source.title}
        </div>
        <div className="flex items-center gap-1 text-[13px] text-[hsl(var(--source-info))]">
          <span>{source.year}</span>
          <span>·</span>
          <span>{source.span}</span>
        </div>
      </CardContent>
    </Card>
  );
}
