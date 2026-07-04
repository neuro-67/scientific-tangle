type Props = {
  text: string;
};

export function EmptyState({ text }: Props) {
  return (
    <div className="rounded-2xl border border-dashed border-input bg-background/50 p-6 text-center text-sm text-description">
      {text}
    </div>
  );
}
