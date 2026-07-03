import { Skeleton } from "@/shared/ui";

/** Loading placeholder shown while the query is being answered. */
export function AnswerSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-6 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    </div>
  );
}
