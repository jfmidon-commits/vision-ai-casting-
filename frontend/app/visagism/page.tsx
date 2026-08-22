"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  PhotoUploadGuide,
  VisagismPhotoAngle,
  VisagismPhotoDraft,
} from "@/components/visagism/photo-upload-guide";

type Step = "landing" | "upload" | "review";

const initialPhotos: VisagismPhotoDraft[] = [
  {
    angle: "front",
    label: "Frontal",
    instruction: "Olhe diretamente para a câmera.",
  },
  {
    angle: "three_quarter",
    label: "3/4",
    instruction: "Vire levemente o rosto.",
  },
  {
    angle: "profile",
    label: "Perfil",
    instruction: "Vire o rosto de lado.",
  },
];

export default function VisagismPage() {
  const [step, setStep] = useState<Step>("landing");
  const [photos, setPhotos] = useState<VisagismPhotoDraft[]>(initialPhotos);

  const selectedCount = useMemo(() => photos.filter((photo) => photo.file).length, [photos]);

  const handlePhotoChange = (angle: VisagismPhotoAngle, file: File) => {
    setPhotos((current) =>
      current.map((photo) => {
        if (photo.angle !== angle) return photo;
        if (photo.previewUrl) URL.revokeObjectURL(photo.previewUrl);
        return {
          ...photo,
          file,
          previewUrl: URL.createObjectURL(file),
        };
      })
    );
  };

  if (step === "upload") {
    return (
      <PhotoUploadGuide
        photos={photos}
        onPhotoChange={handlePhotoChange}
        onContinue={() => setStep("review")}
      />
    );
  }

  if (step === "review") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-4 pb-8 pt-5">
        <button
          type="button"
          className="mb-5 w-fit text-sm font-medium text-muted-foreground"
          onClick={() => setStep("upload")}
        >
          ← Voltar
        </button>

        <div>
          <p className="text-sm font-medium text-muted-foreground">Revisão</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Confira suas fotos</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Na próxima etapa cada foto será enviada e validada pela triagem antes da análise.
          </p>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          {photos.map((photo, index) => (
            <article key={photo.angle} className="overflow-hidden rounded-xl border bg-card">
              {photo.previewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={photo.previewUrl} alt={photo.label} className="aspect-[4/3] w-full object-cover" />
              ) : (
                <div className="flex aspect-[4/3] items-center justify-center bg-muted text-xs text-muted-foreground">
                  Sem foto
                </div>
              )}
              <div className="p-3">
                <p className="text-xs text-muted-foreground">Foto {index + 1}</p>
                <p className="font-medium">{photo.label}</p>
                <p className="mt-1 text-xs text-muted-foreground">Aguardando triagem</p>
              </div>
            </article>
          ))}
        </div>

        <div className="mt-auto pt-8">
          <div className="mb-3 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            {selectedCount} de {photos.length} fotos prontas. O envio real será conectado ao backend no próximo bloco.
          </div>
          <Button className="h-12 w-full text-base" disabled>
            Enviar para análise
          </Button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-5 pb-8 pt-10">
      <div className="flex flex-1 flex-col justify-center">
        <div className="mb-7 flex h-20 w-20 items-center justify-center rounded-3xl border bg-muted text-3xl" aria-hidden="true">
          ✂️
        </div>

        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Vision</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Descubra o corte que valoriza seu rosto</h1>
        <p className="mt-4 text-base leading-7 text-muted-foreground">
          Envie três fotos e receba uma análise baseada nas características reais do seu rosto e cabelo.
        </p>

        <div className="mt-7 space-y-3 rounded-2xl border bg-card p-4 text-sm">
          <div className="flex items-center gap-3"><span className="font-semibold">1.</span><span>Frontal</span></div>
          <div className="flex items-center gap-3"><span className="font-semibold">2.</span><span>3/4</span></div>
          <div className="flex items-center gap-3"><span className="font-semibold">3.</span><span>Perfil</span></div>
        </div>
      </div>

      <div className="pt-8">
        <Button className="h-12 w-full text-base" onClick={() => setStep("upload")}>
          Começar agora
        </Button>
        <p className="mt-3 text-center text-xs text-muted-foreground">Etapa inicial: fotos e validação</p>
      </div>
    </main>
  );
}
