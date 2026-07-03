import type { AnswerSource } from "@/entities/query";
import { Badge, Card, CardContent } from "@/shared/ui";

import {
  confidenceLabel,
  confidenceVariant,
  geographyLabel,
  geographyVariant,
} from "../lib/confidence";

type Props = {
  source: AnswerSource;
};

/** Compact citation card: title, year, geography, confidence, span. */
export function SourceCard({ source }: Props) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 p-4">
        <div className="font-medium">{source.title}</div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{source.year}</span>
          <span>·</span>
          <span>{source.span}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={geographyVariant(source.geography)}>
            {geographyLabel(source.geography)}
          </Badge>
          <Badge variant={confidenceVariant(source.confidence)}>
            {confidenceLabel(source.confidence)}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
