import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { lazy, Suspense, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { queryApi, searchParamsToRequest } from "@/entities/query";
import { ROUTES } from "@/shared/constants";
import { handleApiError } from "@/shared/lib/api-error";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Skeleton,
} from "@/shared/ui";

import { confidenceLabel, confidenceVariant } from "../lib/confidence";
import { AnswerSkeleton } from "./answer-skeleton";
import { SourceCard } from "./source-card";

// Cytoscape is heavy; load it only when an answer with a subgraph is shown.
const SubgraphView = lazy(() =>
  import("./subgraph-view").then((m) => ({ default: m.SubgraphView }))
);

/** Answer screen: renders the cited, structured answer for a question. */
export function AnswerPage() {
  const [searchParams] = useSearchParams();
  const request = useMemo(
    () => searchParamsToRequest(searchParams),
    [searchParams]
  );

  const answerQuery = useQuery(queryApi.queries.ask(request));
  const data = answerQuery.data;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Button asChild variant="ghost" size="sm" className="w-fit">
          <Link to={ROUTES.search}>
            <ArrowLeft />
            Новый поиск
          </Link>
        </Button>
        <h1 className="text-xl font-semibold">
          {request.question || "Вопрос не задан"}
        </h1>
      </div>

      {answerQuery.isPending && request.question ? <AnswerSkeleton /> : null}

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

      {data ? (
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle>Ответ</CardTitle>
              <Badge variant={confidenceVariant(data.confidence)}>
                {confidenceLabel(data.confidence)}
              </Badge>
            </CardHeader>
            <CardContent className="whitespace-pre-wrap leading-relaxed">
              {data.answer}
            </CardContent>
          </Card>

          {data.subgraph.nodes.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Подграф знаний</CardTitle>
              </CardHeader>
              <CardContent>
                <Suspense fallback={<Skeleton className="h-80 w-full" />}>
                  <SubgraphView subgraph={data.subgraph} />
                </Suspense>
              </CardContent>
            </Card>
          ) : null}

          {data.consensus.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Консенсус</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 text-sm">
                {data.consensus.map((point) => (
                  <span key={point}>— {point}</span>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {data.disagreements.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Противоречия
                  <Badge variant="contradiction">
                    {data.disagreements.length}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                {data.disagreements.map((d) => (
                  <div key={d.point} className="flex flex-col gap-1">
                    <span className="font-medium">{d.point}</span>
                    <span className="text-muted-foreground">
                      {d.sources_a.join(", ")} ↔ {d.sources_b.join(", ")}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {data.gaps.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Badge variant="gap">пробелы</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 text-sm">
                {data.gaps.map((gap) => (
                  <span key={gap}>— {gap}</span>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {data.sources.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-medium text-muted-foreground">
                Источники
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {data.sources.map((source, i) => (
                  <SourceCard key={`${source.title}-${i}`} source={source} />
                ))}
              </div>
            </section>
          ) : null}

          {data.experts.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Эксперты</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 text-sm">
                {data.experts.map((expert) => (
                  <span key={expert.name}>
                    {expert.name}
                    <span className="text-muted-foreground">
                      {" "}
                      — {expert.affiliation}
                    </span>
                  </span>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
