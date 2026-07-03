import type { QueryFilters } from "@/entities/query";
import type { ConfidenceLevel, Geography } from "@/shared/types";
import {
  Input,
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

const toNum = (raw: string): number | null => (raw === "" ? null : Number(raw));

/** Filter panel: material / process / geography / year / numeric range. */
export function SearchFilters({ filters, onChange }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <Label htmlFor="materials">Материалы</Label>
        <TagInput
          id="materials"
          value={filters.materials}
          onChange={(materials) => onChange({ materials })}
          placeholder="сульфаты, хлориды…"
        />
      </div>

      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <Label htmlFor="processes">Процессы</Label>
        <TagInput
          id="processes"
          value={filters.processes}
          onChange={(processes) => onChange({ processes })}
          placeholder="обессоливание, электроэкстракция…"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="geography">География</Label>
        <Select
          value={filters.geography}
          onValueChange={(geography) =>
            onChange({ geography: geography as Geography })
          }
        >
          <SelectTrigger id="geography">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Все</SelectItem>
            <SelectItem value="RU">Отечественные</SelectItem>
            <SelectItem value="foreign">Зарубежные</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confidence">Уровень достоверности</Label>
        <Select
          value={filters.confidence}
          onValueChange={(confidence) =>
            onChange({
              confidence: confidence as ConfidenceLevel | "any",
            })
          }
        >
          <SelectTrigger id="confidence">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Любой</SelectItem>
            <SelectItem value="high">Высокий</SelectItem>
            <SelectItem value="medium">Средний и выше</SelectItem>
            <SelectItem value="low">Любой (вкл. низкий)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <Label>Год публикации</Label>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            inputMode="numeric"
            placeholder="от"
            value={filters.yearFrom ?? ""}
            onChange={(e) => onChange({ yearFrom: toNum(e.target.value) })}
          />
          <span className="text-muted-foreground">—</span>
          <Input
            type="number"
            inputMode="numeric"
            placeholder="до"
            value={filters.yearTo ?? ""}
            onChange={(e) => onChange({ yearTo: toNum(e.target.value) })}
          />
        </div>
      </div>
    </div>
  );
}
