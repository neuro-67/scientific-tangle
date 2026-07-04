import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { documentApi, type Document } from "@/entities/document";
import { handleApiError } from "@/shared/lib/api-error";

import { DocumentRow } from "./document-row";
import { UploadDropzone } from "./upload-dropzone";

/** Screen for uploading new documents into the corpus and tracking ingestion. */
export function UploadPage() {
  const [items, setItems] = useState<Document[]>([]);

  const uploadMutation = useMutation({
    mutationFn: documentApi.uploadDocument,
    onSuccess: (document) => {
      setItems((prev) => [document, ...prev]);
    },
    onError: (error) => {
      handleApiError(error, { fallback: "Не удалось загрузить документ" });
    },
  });

  const handleFiles = (files: File[]) => {
    files.forEach((file) => {
      uploadMutation.mutate(
        { file },
        {
          onSuccess: () => toast.success(`«${file.name}» загружен в очередь`),
        }
      );
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
      <div>
        <h1 className="text-[34px] font-bold leading-tight text-foreground">
          Загрузка документов
        </h1>
        <p className="mt-1 text-base text-description">
          Добавьте новые источники — они будут обработаны и добавлены в корпус
        </p>
      </div>

      <UploadDropzone
        onFiles={handleFiles}
        disabled={uploadMutation.isPending}
      />

      {items.length > 0 ? (
        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-foreground">
            Загруженные документы
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {items.map((doc) => (
              <DocumentRow key={doc.id} document={doc} />
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-input bg-card p-10 text-center text-description">
          Пока нет загруженных документов в этой сессии.
        </div>
      )}
    </div>
  );
}
