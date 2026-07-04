import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  addQueryHistory,
  filtersToRequest,
  getQueryHistory,
  removeQueryHistory,
  requestToSearchParams,
  toggleQueryHistoryFavorite,
} from "@/entities/query";
import { ROUTES } from "@/shared/constants";
import { Button } from "@/shared/ui";

type Tab = "all" | "favorite";

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Query history screen with all queries and favorites. */
export function HistoryPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [items, setItems] = useState(() => getQueryHistory());

  const filtered = useMemo(
    () => items.filter((i) => (tab === "favorite" ? i.favorite : true)),
    [items, tab]
  );

  const toggleFavorite = (id: string) => {
    toggleQueryHistoryFavorite(id);
    setItems(getQueryHistory());
  };

  const remove = (id: string) => {
    removeQueryHistory(id);
    setItems(getQueryHistory());
  };

  const handleExample = () => {
    addQueryHistory(
      "При каких параметрах эффективно обессоливание пластовых вод?",
      {
        question:
          "При каких параметрах эффективно обессоливание пластовых вод?",
        materials: ["сульфаты", "хлориды"],
        processes: ["обессоливание"],
        geography: "any",
        dateFrom: "2025-12-31",
        dateTo: "2026-06-21",
        confidence: "any",
      },
      true
    );
    setItems(getQueryHistory());
  };

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
      <div>
        <h1 className="text-[34px] font-bold leading-tight text-foreground">
          История запросов
        </h1>
        <p className="mt-1 text-base text-description">
          Все запросы и избранные ответы
        </p>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setTab("all")}
          className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
            tab === "all"
              ? "bg-primary text-white"
              : "bg-card text-foreground hover:bg-muted"
          }`}
        >
          Все запросы
        </button>
        <button
          type="button"
          onClick={() => setTab("favorite")}
          className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
            tab === "favorite"
              ? "bg-primary text-white"
              : "bg-card text-foreground hover:bg-muted"
          }`}
        >
          Избранное
        </button>
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-input bg-card p-10 text-center">
          <span className="text-description">
            {tab === "favorite"
              ? "Пока нет избранных запросов."
              : "История запросов пуста."}
          </span>
          {tab === "all" ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={handleExample}
                className="rounded-xl"
              >
                Добавить пример запроса
              </Button>
              <Link
                to={ROUTES.search}
                className="text-sm font-medium text-primary hover:underline"
              >
                Перейти к поиску
              </Link>
            </>
          ) : (
            <Link
              to={ROUTES.search}
              className="text-sm font-medium text-primary hover:underline"
            >
              Перейти к поиску
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filtered.map((item) => {
            const params = requestToSearchParams(
              filtersToRequest(item.filters)
            );
            return (
              <div
                key={item.id}
                className="flex items-start justify-between gap-4 rounded-2xl border border-input bg-card p-5"
              >
                <div className="flex flex-col gap-1">
                  <Link
                    to={`${ROUTES.answer}?${params.toString()}`}
                    className="text-[17px] font-semibold text-foreground hover:text-primary"
                  >
                    {item.question}
                  </Link>
                  <span className="text-xs text-description">
                    {formatDate(item.createdAt)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleFavorite(item.id)}
                    title={
                      item.favorite ? "Убрать из избранного" : "В избранное"
                    }
                    className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                      item.favorite
                        ? "border-yellow-400 bg-yellow-50 text-yellow-600"
                        : "border-input bg-card text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    <img
                      src="/assets/icon-star.png"
                      alt=""
                      className={`h-4 w-4 object-contain ${
                        item.favorite ? "" : "brightness-0"
                      }`}
                    />
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(item.id)}
                    title="Удалить"
                    className="flex h-9 w-9 items-center justify-center rounded-xl border border-input bg-card text-muted-foreground transition-colors hover:bg-destructive hover:text-destructive-foreground"
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
