import { Input } from "./input";

type Props = {
  from: string | null;
  to: string | null;
  onFromChange: (value: string | null) => void;
  onToChange: (value: string | null) => void;
  className?: string;
};

const INPUT_CLASS =
  "h-12 flex-1 rounded-xl border border-input bg-card px-3 text-center text-sm text-main focus-visible:ring-1 focus-visible:ring-ring";

/** Two native date inputs for selecting a [from, to] range. */
export function DateRangeInput({
  from,
  to,
  onFromChange,
  onToChange,
  className,
}: Props) {
  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      <Input
        type="date"
        value={from ?? ""}
        onChange={(e) => onFromChange(e.target.value || null)}
        className={INPUT_CLASS}
      />
      <span className="text-description">—</span>
      <Input
        type="date"
        value={to ?? ""}
        onChange={(e) => onToChange(e.target.value || null)}
        className={INPUT_CLASS}
      />
    </div>
  );
}
