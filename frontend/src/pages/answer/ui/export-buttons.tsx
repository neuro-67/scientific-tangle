import { toast } from "sonner";

import type { QueryAnswer } from "@/entities/query";
import {
  downloadText,
  printHtml,
  slugify,
  toJsonLd,
  toMarkdown,
  toPrintableHtml,
} from "@/shared/lib/export";

type Props = {
  question: string;
  answer: QueryAnswer;
};

/**
 * Three-way export widget shown on the answer screen: Markdown for pasting
 * into technical assignments, JSON-LD for downstream machine consumption,
 * and print-to-PDF for slide decks/reports.
 */
export function ExportButtons({ question, answer }: Props) {
  const stem = slugify(question);

  const handleMarkdown = () => {
    try {
      downloadText(toMarkdown(question, answer), `${stem}.md`, "text/markdown");
      toast.success("Markdown-файл скачан");
    } catch (error) {
      toast.error("Не удалось сохранить Markdown");
      console.error(error);
    }
  };

  const handleJsonLd = () => {
    try {
      const json = JSON.stringify(toJsonLd(question, answer), null, 2);
      downloadText(json, `${stem}.jsonld`, "application/ld+json");
      toast.success("JSON-LD скачан");
    } catch (error) {
      toast.error("Не удалось сохранить JSON-LD");
      console.error(error);
    }
  };

  const handlePdf = () => {
    try {
      printHtml(toPrintableHtml(question, answer));
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Не удалось открыть окно печати"
      );
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handlePdf}
        className="h-10 rounded-xl border border-input bg-card px-3 text-sm font-medium text-main transition-colors hover:bg-[hsl(var(--save-hover))]"
        title="Открыть окно печати → сохранить как PDF"
      >
        PDF
      </button>
      <button
        type="button"
        onClick={handleMarkdown}
        className="h-10 rounded-xl border border-input bg-card px-3 text-sm font-medium text-main transition-colors hover:bg-[hsl(var(--save-hover))]"
        title="Скачать Markdown — удобно вставить в ТЗ или заметки"
      >
        Markdown
      </button>
      <button
        type="button"
        onClick={handleJsonLd}
        className="h-10 rounded-xl border border-input bg-card px-3 text-sm font-medium text-main transition-colors hover:bg-[hsl(var(--save-hover))]"
        title="Скачать JSON-LD (schema.org Report) — для интеграций"
      >
        JSON-LD
      </button>
    </div>
  );
}
