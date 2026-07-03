import { Search } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  emptyQueryFilters,
  filtersToRequest,
  requestToSearchParams,
  type QueryFilters,
} from "@/entities/query";
import { ROUTES } from "@/shared/constants";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Textarea,
} from "@/shared/ui";

import { SearchFilters } from "./search-filters";

const EXAMPLE_QUESTIONS = [
  "При каких параметрах эффективно обессоливание пластовых вод?",
  "Оптимальная скорость циркуляции католита при электроэкстракции?",
  "Сравни отечественную и зарубежную практику извлечения Au/Ag/МПГ",
];

/** Search screen: natural-language question + structured filter panel. */
export function SearchPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<QueryFilters>(emptyQueryFilters);

  const patch = (next: Partial<QueryFilters>) =>
    setFilters((prev) => ({ ...prev, ...next }));

  const runSearch = (current: QueryFilters) => {
    if (!current.question.trim()) return;
    const params = requestToSearchParams(filtersToRequest(current));
    navigate(`${ROUTES.answer}?${params.toString()}`);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    runSearch(filters);
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Задайте вопрос корпусу R&amp;D</CardTitle>
          <CardDescription>
            Структурированный ответ с цитатами, уровнем достоверности и
            подграфом знаний.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <Textarea
              value={filters.question}
              onChange={(e) => patch({ question: e.target.value })}
              placeholder="Например: при каких параметрах эффективно обессоливание воды?"
              autoFocus
            />
            <SearchFilters filters={filters} onChange={patch} />
            <Button type="submit" className="self-end">
              <Search />
              Найти
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-2">
        <span className="text-sm text-muted-foreground">Примеры вопросов</span>
        {EXAMPLE_QUESTIONS.map((q) => (
          <Button
            key={q}
            variant="outline"
            className="h-auto justify-start whitespace-normal py-2 text-left"
            onClick={() => runSearch({ ...emptyQueryFilters(), question: q })}
          >
            {q}
          </Button>
        ))}
      </div>
    </div>
  );
}
