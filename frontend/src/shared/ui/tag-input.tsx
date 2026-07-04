import { X } from "lucide-react";
import { type KeyboardEvent, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { Badge } from "./badge";

type Props = {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  className?: string;
  id?: string;
  icon?: string;
};

/**
 * Generic chip/tag input: type a value and press Enter (or comma) to add it.
 * Used for free-form multi-select filters like materials and processes.
 */
function TagInput({
  value,
  onChange,
  placeholder,
  className,
  id,
  icon,
}: Props) {
  const [draft, setDraft] = useState("");

  const add = (raw: string) => {
    const tag = raw.trim();
    if (!tag || value.includes(tag)) return;
    onChange([...value, tag]);
    setDraft("");
  };

  const remove = (tag: string) => onChange(value.filter((t) => t !== tag));

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(draft);
    } else if (e.key === "Backspace" && !draft && value.length) {
      remove(value[value.length - 1]);
    }
  };

  return (
    <div
      className={cn(
        "flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-lg border border-input bg-card px-2 py-1.5 text-sm shadow-sm focus-within:ring-1 focus-within:ring-ring",
        className
      )}
    >
      {icon ? (
        <img src={icon} alt="" className="h-5 w-5 shrink-0 object-contain" />
      ) : null}
      {value.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1">
          {tag}
          <button
            type="button"
            onClick={() => remove(tag)}
            className="text-muted-foreground hover:text-foreground"
            aria-label={`Удалить ${tag}`}
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
      <input
        id={id}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => add(draft)}
        placeholder={value.length ? undefined : placeholder}
        className="min-w-24 flex-1 bg-transparent text-sm text-main outline-none placeholder:text-placeholder"
      />
    </div>
  );
}

export { TagInput };
