import type { QueryFilters } from "@/entities/query";
import type { ConfidenceLevel, Geography } from "@/shared/types";
import {
  DateRangeInput,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  TagInput,
} from "@/shared/ui";

type Props = {
  filters: QueryFilters;
  onChange: (patch: Partial<QueryFilters>) => void;
};

const FIELD_CLASS =
  "h-12 rounded-xl border border-input bg-card px-3 text-sm text-main focus:ring-1 focus:ring-ring";

function IconSelect({
  icon,
  children,
  value,
  onValueChange,
}: {
  icon: string;
  children: React.ReactNode;
  value: string;
  onValueChange: (value: string) => void;
}) {
  return (
    <div className="relative">
      <img
        src={icon}
        alt=""
        className="pointer-events-none absolute left-3 top-1/2 z-10 h-5 w-5 -translate-y-1/2 object-contain"
      />
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className={`${FIELD_CLASS} pl-10`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>{children}</SelectContent>
      </Select>
    </div>
  );
}

/** Filter panel laid out to fit a single viewport. */
export function SearchFilters({ filters, onChange }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div className="flex flex-col gap-1.5">
        <Label
          className="text-[13px] font-semibold text-label"
          htmlFor="materials"
        >
          Материалы
        </Label>
        <TagInput
          id="materials"
          icon="/assets/icon-flask-small.png"
          value={filters.materials}
          onChange={(materials) => onChange({ materials })}
          placeholder="сульфаты, хлориды…"
          className="min-h-12 items-center gap-2 rounded-xl border-input bg-card px-3 py-2 text-sm text-main"
        />
      </div>

      <div className="flex flex-col gap-1.5 md:col-span-2 lg:col-span-2">
        <Label
          className="text-[13px] font-semibold text-label"
          htmlFor="processes"
        >
          Процессы
        </Label>
        <TagInput
          id="processes"
          icon="/assets/icon-settings.png"
          value={filters.processes}
          onChange={(processes) => onChange({ processes })}
          placeholder="обессоливание, электроэкстракция…"
          className="min-h-12 items-center gap-2 rounded-xl border-input bg-card px-3 py-2 text-sm text-main"
        />
      </div>

      <div className="flex flex-col gap-1.5 lg:col-start-1 lg:row-start-2">
        <Label
          className="text-[13px] font-semibold text-label"
          htmlFor="geography"
        >
          География
        </Label>
        <IconSelect
          icon="/assets/icon-share.png"
          value={filters.geography}
          onValueChange={(geography) =>
            onChange({ geography: geography as Geography })
          }
        >
          <SelectItem value="any">Все страны</SelectItem>
          <SelectItem value="RU">Отечественные</SelectItem>
          <SelectItem value="foreign">Зарубежные</SelectItem>
        </IconSelect>
      </div>

      <div className="flex flex-col gap-1.5 lg:col-start-2 lg:row-start-2">
        <Label
          className="text-[13px] font-semibold text-label"
          htmlFor="confidence"
        >
          Уровень достоверности
        </Label>
        <IconSelect
          icon="/assets/icon-shield.png"
          value={filters.confidence}
          onValueChange={(confidence) =>
            onChange({
              confidence: confidence as ConfidenceLevel | "any",
            })
          }
        >
          <SelectItem value="any">Любой</SelectItem>
          <SelectItem value="high">Высокий</SelectItem>
          <SelectItem value="medium">Средний и выше</SelectItem>
          <SelectItem value="low">Любой (вкл. низкий)</SelectItem>
        </IconSelect>
      </div>

      <div className="flex flex-col gap-1.5 md:col-span-2 lg:col-span-1 lg:col-start-3 lg:row-start-2">
        <Label className="text-[13px] font-semibold text-label">
          Год публикации (От / До)
        </Label>
        <DateRangeInput
          from={filters.dateFrom}
          to={filters.dateTo}
          onFromChange={(dateFrom) => onChange({ dateFrom })}
          onToChange={(dateTo) => onChange({ dateTo })}
        />
      </div>
    </div>
  );
}
