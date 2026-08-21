"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  resolveVisagismCardMedia,
  VisagismCardMediaError,
} from "@/lib/visagism-card-media";

type Props = {
  analysis: any;
};

export function IdentityLockedVisagismCard({ analysis }: Props) {
  let media;

  try {
    media = resolveVisagismCardMedia(analysis?.card_media);
  } catch (error) {
    const reason =
      error instanceof VisagismCardMediaError ? error.message : "card_media_invalid";

    return (
      <Card data-testid="visagism-card-blocked" className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-base">Card bloqueado por segurança</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>O Vision não encontrou uma foto real verificada da pessoa analisada.</p>
          <p>Nenhuma imagem gerada será usada como substituta.</p>
          <p className="text-xs">Motivo: {reason}</p>
        </CardContent>
      </Card>
    );
  }

  const recommendation =
    analysis?.visagism?.primary_recommendation ||
    analysis?.visagism?.recommendation ||
    analysis?.analysis?.primary_recommendation ||
    "Recomendação de visagismo";

  return (
    <Card data-testid="identity-locked-visagism-card" className="overflow-hidden">
      <div className="grid gap-0 md:grid-cols-[minmax(220px,0.9fr)_1.1fr]">
        <div className="relative min-h-[280px] bg-muted">
          {/* Native img is intentional here: card media can come from authenticated/local analysis URLs. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={media.displayImage}
            alt="Foto real da pessoa analisada com simulação de cabelo/barba quando validada"
            className="h-full min-h-[280px] w-full object-cover"
            data-testid="visagism-display-image"
          />
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            <Badge variant="secondary">Foto real verificada</Badge>
            {media.simulationApplied ? (
              <Badge>Overlay cabelo/barba validado</Badge>
            ) : (
              <Badge variant="outline">Foto original</Badge>
            )}
          </div>
        </div>

        <div className="p-6">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Vision • Visagismo
              </p>
              <h3 className="mt-1 text-xl font-semibold">{recommendation}</h3>
            </div>
            <Badge variant={media.identityVerified ? "default" : "secondary"}>
              {media.identityVerified ? "Identidade validada" : "Original preservada"}
            </Badge>
          </div>

          <div className="space-y-3 text-sm">
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="font-medium">Âncora de identidade</p>
              <p className="mt-1 text-muted-foreground">
                Este card sempre mantém a foto real usada na análise como origem obrigatória.
              </p>
            </div>
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="font-medium">Regra de simulação</p>
              <p className="mt-1 text-muted-foreground">
                Somente cabelo e barba podem mudar. Rosto, pele, expressão, corpo, roupa e fundo permanecem protegidos.
              </p>
            </div>
            {media.simulationApplied && (
              <div className="rounded-lg border bg-muted/30 p-3" data-testid="original-anchor">
                <p className="font-medium">Foto original preservada no card</p>
                <p className="mt-1 break-all text-xs text-muted-foreground">{media.personPhoto}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
