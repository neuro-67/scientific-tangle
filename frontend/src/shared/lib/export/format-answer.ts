import type { QueryAnswer } from "@/entities/query";

/** Slugify a question into a safe filename stem (Cyrillic-friendly). */
export const slugify = (text: string, max = 60): string => {
  const cleaned = text
    .trim()
    .replace(/[\\/:*?"<>|]+/g, "")
    .replace(/\s+/g, "-");
  return cleaned.slice(0, max) || "answer";
};

/** Human-readable Markdown report — designed to be pasted into TZ / docs. */
export const toMarkdown = (question: string, answer: QueryAnswer): string => {
  const lines: string[] = [];
  lines.push(`# ${question || "Ответ"}`);
  lines.push("");
  lines.push(`_Уверенность: **${answer.confidence}**_`);
  lines.push("");
  lines.push("## Ответ");
  lines.push("");
  lines.push(answer.answer || "—");
  lines.push("");

  if (answer.comparison_table.length) {
    lines.push("## Таблица сравнения");
    lines.push("");
    lines.push(`| Критерий | ${answer.spec.materials[0] ?? answer.spec.processes[0] ?? "Вариант A"} | ${answer.spec.compare ?? "Вариант B"} |`);
    lines.push("|---|---|---|");
    for (const row of answer.comparison_table) {
      lines.push(`| ${row.criterion} | ${row.side_a || "нет данных"} | ${row.side_b || "нет данных"} |`);
    }
    lines.push("");
  }

  const section = (title: string, items: string[]) => {
    if (!items.length) return;
    lines.push(`## ${title}`);
    lines.push("");
    for (const item of items) lines.push(`- ${item}`);
    lines.push("");
  };

  section("Консенсус", answer.consensus);
  section("Пробелы", answer.gaps);

  if (answer.disagreements.length) {
    lines.push("## Противоречия");
    lines.push("");
    lines.push("| Тезис | Сторона A | Сторона B |");
    lines.push("|---|---|---|");
    for (const d of answer.disagreements) {
      lines.push(
        `| ${d.point} | ${d.sources_a.join(", ") || "—"} | ${d.sources_b.join(", ") || "—"} |`
      );
    }
    lines.push("");
  }

  if (answer.experts.length) {
    lines.push("## Эксперты");
    lines.push("");
    for (const e of answer.experts) {
      lines.push(`- **${e.name}** — ${e.affiliation || "—"}`);
    }
    lines.push("");
  }

  if (answer.laboratories.length) {
    lines.push("## Лаборатории");
    lines.push("");
    for (const l of answer.laboratories) {
      lines.push(`- **${l.name}** — ${l.institution || "—"}`);
    }
    lines.push("");
  }

  if (answer.sources.length) {
    lines.push("## Источники");
    lines.push("");
    for (const s of answer.sources) {
      const parts = [
        s.title,
        s.year ? `(${s.year})` : null,
        s.geography && s.geography !== "any" ? s.geography : null,
        s.span,
        `уверенность: ${s.confidence}`,
      ].filter(Boolean);
      lines.push(`- ${parts.join(", ")}`);
    }
    lines.push("");
  }

  return lines.join("\n");
};

/**
 * JSON-LD envelope loosely following schema.org/Report. Machine-readable and
 * easy for downstream tools (Zotero, custom ingestion) to consume.
 */
export const toJsonLd = (
  question: string,
  answer: QueryAnswer
): Record<string, unknown> => ({
  "@context": "https://schema.org",
  "@type": "Report",
  name: question,
  headline: question,
  dateCreated: new Date().toISOString(),
  inLanguage: "ru",
  about: {
    "@type": "Question",
    text: question,
  },
  text: answer.answer,
  additionalProperty: [
    { "@type": "PropertyValue", name: "confidence", value: answer.confidence },
    { "@type": "PropertyValue", name: "intent", value: answer.spec.intent },
  ],
  keywords: [...answer.spec.materials, ...answer.spec.processes].join(", "),
  citation: answer.sources.map((s) => ({
    "@type": "CreativeWork",
    name: s.title,
    datePublished: s.year ?? undefined,
    locationCreated: s.geography !== "any" ? s.geography : undefined,
    pagination: s.span ?? undefined,
    additionalProperty: [
      { "@type": "PropertyValue", name: "confidence", value: s.confidence },
      s.extracted_at
        ? { "@type": "PropertyValue", name: "extractedAt", value: s.extracted_at }
        : null,
    ].filter(Boolean),
  })),
  author: answer.experts.map((e) => ({
    "@type": "Person",
    name: e.name,
    affiliation: e.affiliation || undefined,
  })),
  mentions: [
    ...answer.consensus.map((c) => ({ "@type": "Claim", text: c, claimInterpreter: "consensus" })),
    ...answer.gaps.map((g) => ({ "@type": "Claim", text: g, claimInterpreter: "gap" })),
    ...answer.disagreements.map((d) => ({
      "@type": "Claim",
      text: d.point,
      claimInterpreter: "disagreement",
      supportingItem: d.sources_a,
      counterItem: d.sources_b,
    })),
  ],
  ...(answer.comparison_table.length
    ? {
        comparisonTable: answer.comparison_table.map((row) => ({
          "@type": "PropertyValue",
          name: row.criterion,
          value: [row.side_a || "нет данных", row.side_b || "нет данных"],
        })),
      }
    : {}),
});

/** Escapes text for safe embedding into HTML. */
const escapeHtml = (s: string): string =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/**
 * Print-optimized HTML document. Opened in a new window and `window.print()`d
 * so the user can save as PDF from the browser's print dialog — avoids
 * pulling a heavy jsPDF/html2pdf dependency into the bundle for a feature
 * that's rarely on the critical path.
 */
export const toPrintableHtml = (question: string, answer: QueryAnswer): string => {
  const md = toMarkdown(question, answer);
  // Trivial markdown → HTML — good enough for print output.
  const htmlBody = md
    .split("\n")
    .map((line) => {
      if (line.startsWith("# ")) return `<h1>${escapeHtml(line.slice(2))}</h1>`;
      if (line.startsWith("## ")) return `<h2>${escapeHtml(line.slice(3))}</h2>`;
      if (line.startsWith("- ")) return `<li>${escapeHtml(line.slice(2))}</li>`;
      if (line.startsWith("|")) return `<div class="row">${escapeHtml(line)}</div>`;
      if (line.startsWith("_") && line.endsWith("_"))
        return `<p class="meta">${escapeHtml(line.slice(1, -1))}</p>`;
      if (!line.trim()) return "";
      return `<p>${escapeHtml(line)}</p>`;
    })
    .join("\n")
    .replace(/(<li>.*?<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

  return `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>${escapeHtml(question)}</title>
<style>
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; max-width: 780px; margin: 2rem auto; padding: 0 1rem; color: #111; line-height: 1.5; }
  h1 { font-size: 22px; margin-bottom: 0.5rem; }
  h2 { font-size: 16px; margin-top: 1.4rem; margin-bottom: 0.5rem; border-bottom: 1px solid #ddd; padding-bottom: 0.2rem; }
  p { margin: 0.4rem 0; }
  ul { padding-left: 1.2rem; margin: 0.3rem 0; }
  .meta { color: #666; font-style: italic; }
  .row { font-family: monospace; font-size: 12px; white-space: pre; }
  @media print { body { max-width: none; margin: 0.5cm; } }
</style>
</head>
<body>
${htmlBody}
</body>
</html>`;
};
