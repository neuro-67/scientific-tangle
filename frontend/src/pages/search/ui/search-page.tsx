import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  emptyQueryFilters,
  filtersToRequest,
  requestToSearchParams,
  type QueryFilters,
} from "@/entities/query";
import { ROUTES } from "@/shared/constants";
import { Button } from "@/shared/ui";

import { SearchFilters } from "./search-filters";

const EXAMPLE_QUESTIONS = [
  "При каких параметрах эффективно обессоливание пластовых вод?",
  "Оптимальная скорость циркуляции католита при электроэкстракции?",
  "Сравни отечественную и зарубежную практику извлечения Au/Ag/МПГ",
];

/** Search screen: natural-language question + structured filter panel. */
export function SearchPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<QueryFilters>({
    ...emptyQueryFilters(),
    dateFrom: "2025-12-31",
    dateTo: "2026-06-21",
  });
  const [showFilters, setShowFilters] = useState(true);

  const patch = (next: Partial<QueryFilters>) =>
    setFilters((prev) => ({ ...prev, ...next }));

  const runSearch = (current: QueryFilters) => {
    if (!current.question.trim()) return;
    // Persistence now happens server-side on POST /query/ask; the answer page
    // reads the question from the URL, invokes the ask endpoint and lands the
    // row in the DB. History gets populated automatically.
    const params = requestToSearchParams(filtersToRequest(current));
    navigate(`${ROUTES.answer}?${params.toString()}`);
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSearch(filters);
  };

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
      <div>
        <h1 className="text-[34px] font-bold leading-tight text-foreground">
          Задайте вопрос корпусу R&amp;D
        </h1>
        <p className="mt-1 text-base text-description">
          Структурированный ответ с цитатами, уровнем достоверности и подграфом
          знаний
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-4 rounded-2xl bg-card p-6"
      >
        <div className="relative">
          <textarea
            value={filters.question}
            onChange={(e) => patch({ question: e.target.value })}
            placeholder="Например: при каких параметрах эффективно обессоливание пластовых вод?"
            className="h-[76px] min-h-0 w-full resize-none rounded-[14px] border border-input bg-card p-4 text-sm text-main placeholder:text-placeholder focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            maxLength={500}
          />
          <span className="absolute bottom-3 right-3 text-xs text-description">
            {filters.question.length}/500
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowFilters((v) => !v)}
          className="flex items-center gap-2 self-start text-sm font-medium text-primary hover:underline"
        >
          <span>Параметры поиска</span>
          <img
            src="/assets/icon-arrow.png"
            alt=""
            className={`h-3 w-3 object-contain transition-transform ${
              showFilters ? "rotate-90" : "-rotate-90"
            }`}
          />
        </button>

        {showFilters ? (
          <>
            <div className="h-px bg-border" />
            <SearchFilters filters={filters} onChange={patch} />
          </>
        ) : null}

        <Button
          type="submit"
          className="h-12 w-full rounded-xl bg-brand-gradient text-base font-semibold text-white shadow-search"
        >
          <img
            src="/assets/icon-search.png"
            alt=""
            className="mr-2 h-5 w-5 object-contain brightness-0 invert"
          />
          Найти
        </Button>
      </form>

      <div className="space-y-2">
        <span className="text-sm text-description">Примеры вопросов</span>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="flex h-[80px] items-start gap-3 rounded-[14px] border border-[#E9ECF8] bg-card p-[18px] text-left text-sm text-main transition-all hover:-translate-y-0.5 hover:border-[#4B63FF] hover:shadow-[0_10px_30px_rgba(76,73,255,0.12)]"
              onClick={() => runSearch({ ...emptyQueryFilters(), question: q })}
            >
              <img
                src="/assets/icon-document.png"
                alt=""
                className="mt-0.5 h-5 w-5 shrink-0 object-contain"
              />
              <span className="line-clamp-2">{q}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
