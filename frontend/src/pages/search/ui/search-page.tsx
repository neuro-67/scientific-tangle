import { Search } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ROUTES } from "@/shared/constants";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
} from "@/shared/ui";

const EXAMPLE_QUESTIONS = [
  "При каких параметрах эффективно обессоливание пластовых вод?",
  "Оптимальная скорость циркуляции католита при электроэкстракции?",
  "Сравни отечественную и зарубежную практику извлечения Au/Ag/МПГ",
];

/** Landing / search screen: enter a natural-language question. */
export function SearchPage() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");

  const submit = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    navigate(`${ROUTES.answer}?q=${encodeURIComponent(trimmed)}`);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit(question);
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
          <form onSubmit={onSubmit} className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Например: параметры обессоливания воды…"
              autoFocus
            />
            <Button type="submit">
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
            className="justify-start text-left"
            onClick={() => submit(q)}
          >
            {q}
          </Button>
        ))}
      </div>
    </div>
  );
}
