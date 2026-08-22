"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { analysisApi } from "@/lib/api";
import type { SimulationPreflightResult, VisagismResult } from "@/types";

interface Props {
  result: VisagismResult;
  analysisId: string | null;
  onReset: () => void;
}

export function VisagismResultView({ result, analysisId, onReset }: Props) {
  const interpretation = result.interpretation;
  const rawHaircuts = (result.recommended_hairstyles || []).filter((item): item is string => typeof item === "string");
  const primaryName = interpretation?.primary_recommendation?.name || result.primary_hairstyle || rawHaircuts[0] || null;
  const [simulation, setSimulation] = useState<SimulationPreflightResult | null>(null);
  const [simulationLoading, setSimulationLoading] = useState(false);

  const runSimulationPreflight = async () => {
    if (!analysisId || !primaryName) return;
    setSimulationLoading(true);
    try {
      const response = await analysisApi.simulateVisagism(analysisId, primaryName);
      setSimulation(response.data?.data as SimulationPreflightResult);
    } finally {
      setSimulationLoading(false);
    }
  };

  if (interpretation?.status === "insufficient_grounded_data") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-4 pb-8 pt-6">
        <p className="text-sm font-medium text-muted-foreground">Resultado</p>
        <h1 className="mt-1 text-2xl font-semibold">Precisamos de fotos melhores</h1>
        <p className="mt-4 text-sm leading-6 text-muted-foreground">{interpretation.executive_summary}</p>
        {interpretation.current_hair_assessment.attention_points.length ? (
          <div className="mt-6 rounded-2xl border bg-card p-4">
            <h2 className="font-semibold">O que faltou confirmar</h2>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {interpretation.current_hair_assessment.attention_points.map((item) => <li key={item}>• {item}</li>)}
            </ul>
          </div>
        ) : null}
        <Button className="mt-auto h-12 w-full" onClick={onReset}>Tentar novamente</Button>
      </main>
    );
  }

  const primary = interpretation?.primary_recommendation;
  const alternatives = interpretation?.alternative_hairstyles || [];
  const brief = interpretation?.barber_brief;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-4 pb-8 pt-6">
      <p className="text-sm font-medium text-muted-foreground">Resultado</p>
      <h1 className="mt-1 text-2xl font-semibold">Sua análise foi concluída</h1>
      {interpretation?.executive_summary ? (
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{interpretation.executive_summary}</p>
      ) : null}

      {primaryName ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Recomendação principal</p>
          <h2 className="mt-2 text-xl font-semibold">{primaryName}</h2>
          {primary?.why_it_works ? <p className="mt-3 text-sm leading-6 text-muted-foreground">{primary.why_it_works}</p> : null}
          {primary?.professional_positioning ? <p className="mt-3 text-sm leading-6">{primary.professional_positioning}</p> : null}
        </section>
      ) : (
        <div className="mt-6 rounded-xl border bg-muted/30 p-4 text-sm text-muted-foreground">Não houve dados suficientes para uma recomendação principal nesta sessão.</div>
      )}

      {alternatives.length ? (
        <section className="mt-6">
          <h2 className="text-base font-semibold">Outras opções</h2>
          <div className="mt-3 space-y-3">
            {alternatives.map((item, index) => (
              <article key={`${item.name}-${index}`} className="rounded-xl border bg-card p-4">
                <p className="text-xs text-muted-foreground">Opção {index + 2}</p>
                <p className="mt-1 font-medium">{item.name}</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.why_it_works}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {brief ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Card do barbeiro</p>
          <h2 className="mt-2 text-lg font-semibold">{brief.recommendation_name || primaryName || "Corte recomendado"}</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div><dt className="font-medium">Topo</dt><dd className="text-muted-foreground">{brief.top}</dd></div>
            <div><dt className="font-medium">Laterais</dt><dd className="text-muted-foreground">{brief.sides}</dd></div>
            <div><dt className="font-medium">Parte de trás</dt><dd className="text-muted-foreground">{brief.back}</dd></div>
            <div><dt className="font-medium">Franja</dt><dd className="text-muted-foreground">{brief.fringe}</dd></div>
            <div><dt className="font-medium">Textura</dt><dd className="text-muted-foreground">{brief.texture}</dd></div>
            <div><dt className="font-medium">Acabamento</dt><dd className="text-muted-foreground">{brief.finish}</dd></div>
          </dl>
          <p className="mt-4 text-xs leading-5 text-muted-foreground">{brief.note}</p>
        </section>
      ) : null}

      {interpretation?.current_hair_assessment ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <h2 className="font-semibold">Seu cabelo hoje</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{interpretation.current_hair_assessment.summary}</p>
          {interpretation.current_hair_assessment.attention_points.length ? (
            <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
              {interpretation.current_hair_assessment.attention_points.map((item) => <li key={item}>• {item}</li>)}
            </ul>
          ) : null}
        </section>
      ) : null}

      {interpretation?.confidence_note ? <p className="mt-5 text-xs leading-5 text-muted-foreground">{interpretation.confidence_note}</p> : null}

      {primaryName && analysisId ? (
        <section className="mt-6">
          <Button variant="outline" className="h-12 w-full" onClick={runSimulationPreflight} disabled={simulationLoading}>
            {simulationLoading ? "Verificando simulação..." : "Ver simulação segura"}
          </Button>
          {simulation ? (
            <div className="mt-3 rounded-2xl border bg-muted/20 p-4">
              {simulation.card_media?.displayImage ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={simulation.card_media.displayImage} alt="Foto original preservada" className="w-full rounded-xl object-cover" />
              ) : null}
              <p className="mt-3 text-sm font-medium">Simulação ainda bloqueada com segurança</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">O Vision manteve sua foto original porque a geração visual pronta para uso ainda não está habilitada.</p>
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="mt-auto pt-8">
        <Button variant="outline" className="h-12 w-full" onClick={onReset}>Fazer nova análise</Button>
      </div>
    </main>
  );
}
