import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function DashboardSection({
  title,
  description,
  children,
  className,
}: Props) {
  return (
    <section
      className={`rounded-[20px] border border-input bg-card p-5 ${className ?? ""}`}
    >
      <div className="mb-4 flex flex-col gap-1">
        <h2 className="text-[18px] font-semibold text-foreground">{title}</h2>
        {description ? (
          <p className="text-sm leading-5 text-description">{description}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}
