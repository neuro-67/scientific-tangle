import { useRef, useState } from "react";

type Props = {
  /** Called with the picked files (drag-drop or file dialog). */
  onFiles: (files: File[]) => void;
  /** Disables interaction while an upload is in flight. */
  disabled?: boolean;
};

/** Accepted source formats, mirrored in the file dialog and the hint text. */
const ACCEPT = ".pdf,.doc,.docx,.txt,.md,.rtf,.html";

/** Drag-and-drop area with a click-to-browse fallback. */
export function UploadDropzone({ onFiles, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const emit = (list: FileList | null) => {
    const files = list ? Array.from(list) : [];
    if (files.length > 0) onFiles(files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!disabled) emit(e.dataTransfer.files);
      }}
      className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
        isDragging
          ? "border-primary bg-accent"
          : "border-input bg-card hover:border-primary/60 hover:bg-accent/40"
      } ${disabled ? "pointer-events-none opacity-60" : ""}`}
    >
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient shadow-sm">
        <img
          src="/assets/icon-cloud.png"
          alt=""
          className="h-7 w-7 object-contain brightness-0 invert"
        />
      </span>
      <div className="flex flex-col gap-1">
        <span className="text-base font-semibold text-foreground">
          Перетащите документы сюда или нажмите, чтобы выбрать
        </span>
        <span className="text-sm text-description">
          PDF, DOC, DOCX, TXT, MD — можно несколько файлов сразу
        </span>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          emit(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
