"use client";

import { ChangeEvent } from "react";
import { Button } from "@/components/ui/button";

export type VisagismPhotoAngle = "front" | "three_quarter" | "profile";

export interface VisagismPhotoDraft {
  angle: VisagismPhotoAngle;
  label: string;
  instruction: string;
  file?: File;
  previewUrl?: string;
}

interface PhotoUploadGuideProps {
  photos: VisagismPhotoDraft[];
  onPhotoChange: (angle: VisagismPhotoAngle, file: File) => void;
  onContinue: () => void;
}

const angleCopy: Record<VisagismPhotoAngle, string> = {
  front: "Olhe diretamente para a câmera, com o rosto relaxado e bem iluminado.",
  three_quarter: "Vire levemente o rosto, mantendo os dois olhos visíveis.",
  profile: "Vire o rosto de lado, sem inclinar a cabeça.",
};

export function PhotoUploadGuide({ photos, onPhotoChange, onContinue }: PhotoUploadGuideProps) {
  const ready = photos.every((photo) => Boolean(photo.file));

  const handleFile = (angle: VisagismPhotoAngle) => (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) onPhotoChange(angle, file);
  };

  return (
    <section className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-4 pb-8 pt-5">
      <div className="mb-6">
        <p className="text-sm font-medium text-muted-foreground">Fotos para análise</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Tire 3 fotos do rosto</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Use luz frontal, fundo simples e evite óculos, boné ou qualquer item cobrindo o rosto.
        </p>
      </div>

      <div className="space-y-4">
        {photos.map((photo, index) => (
          <article key={photo.angle} className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Foto {index + 1} de {photos.length}
                </p>
                <h2 className="mt-1 text-lg font-semibold">{photo.label}</h2>
              </div>
              <span className="rounded-full border px-2.5 py-1 text-xs font-medium">
                {photo.file ? "Selecionada" : "Pendente"}
              </span>
            </div>

            <p className="mt-2 text-sm leading-6 text-muted-foreground">{angleCopy[photo.angle]}</p>

            <div className="mt-4 overflow-hidden rounded-lg border bg-muted/30">
              {photo.previewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={photo.previewUrl} alt={`Prévia ${photo.label}`} className="aspect-[4/3] w-full object-cover" />
              ) : (
                <div className="flex aspect-[4/3] items-center justify-center px-8 text-center text-sm text-muted-foreground">
                  A prévia da foto aparecerá aqui.
                </div>
              )}
            </div>

            <label className="mt-4 block">
              <span className="sr-only">Selecionar foto {photo.label}</span>
              <input
                type="file"
                accept="image/*"
                capture="user"
                className="sr-only"
                onChange={handleFile(photo.angle)}
              />
              <span className="flex h-11 w-full cursor-pointer items-center justify-center rounded-md border border-input bg-background px-4 text-sm font-medium hover:bg-accent">
                {photo.file ? "Trocar foto" : "Usar câmera ou galeria"}
              </span>
            </label>
          </article>
        ))}
      </div>

      <div className="mt-auto pt-6">
        <Button className="h-12 w-full text-base" disabled={!ready} onClick={onContinue}>
          Revisar fotos
        </Button>
        {!ready && (
          <p className="mt-2 text-center text-xs text-muted-foreground">Selecione as três fotos para continuar.</p>
        )}
      </div>
    </section>
  );
}
