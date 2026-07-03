import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { queryApi } from "@/entities/query";
import { handleApiError } from "@/shared/lib/api-error";
import { ROUTES } from "@/shared/constants";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/ui";

import { confidenceLabel, confidenceVariant } from "../lib/confidence";
import { AnswerSkeleton } from "./answer-skeleton";
import { SourceCard } from "./source-card";

/** Answer screen: renders the cited, structured answer for a question. */
export function AnswerPage() {
  const [searchParams] = useSearchParams();
  const question = searchParams.get("q") ?? "";

  const answerQuery = useQuery(queryApi.queries.ask({ question }));

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Button asChild variant="ghost" size="sm" className="w-fit">
          <Link to={ROUTES.search}>
            <ArrowLeft />
            Новый поиск
          </Link>
        </Button>
        <h1 className="text-xl font-semibold">{question || "Вопрос не задан"}</h1>
      </div>

      {answerQuery.isPending && question ? <AnswerSkeleton /> : null}

      {answerQuery.isError ? (
        <Card>
          <CardContent className="p-6 text-sm text-destructive">
            {handleApiError(answerQuery.error, {
              fallback: "Не удалось получить ответ",
              showToast: false,
            })}
          </CardContent>
        </Card>
      ) : null}

      {answerQuery.data ? (
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Ответ</CardTitle>
              <Badge variant={confidenceVariant(answerQuery.data.confidence)}>
                {confidenceLabel(answerQuery.data.confidence)}
              </Badge>
            </CardHeader>
            <CardContent className="whitespace-pre-wrap leading-relaxed">
              {answerQuery.data.answer}
            </CardContent>
          </Card>

          {answerQuery.data.gaps.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Badge variant="gap">пробелы</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 text-sm">
                {answerQuery.data.gaps.map((gap) => (
                  <span key={gap}>— {gap}</span>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {answerQuery.data.sources.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-medium text-muted-foreground">
                Источники
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {answerQuery.data.sources.map((source, i) => (
                  <SourceCard key={`${source.title}-${i}`} source={source} />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
