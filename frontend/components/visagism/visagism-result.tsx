"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { analysisApi } from "@/lib/api";
import type {
  BarberBrief,
  SimulationPreflightResult,
  VisagismResult,
} from "@/types";

interface Props {
  result: VisagismResult;
  analysisId: string | null;
  onReset: () => void;
}

type PreviewMode = "original" | "simulation";

const SIMULATION_REASON_COPY: Record<string, string> = {
  inpaint_provider_not_configured:
    "A geração visual ainda não está configurada. Sua foto original foi preservada.",
  identity_verifier_not_configured:
    "A verificação de identidade não está disponível. Por segurança, nenhuma imagem foi publicada.",
  invalid_reference_count:
    "Não foi possível confirmar referências suficientes da mesma pessoa para gerar esta prévia com segurança.",
  reference_identity_gate_failed:
    "As fotos de referência não passaram pela confirmação de identidade necessária para esta prévia.",
  face_not_detected:
    "Não foi possível localizar o rosto com segurança para delimitar a área do cabelo.",
  person_segmentation_failed:
    "Não foi possível separar com segurança a pessoa do fundo nesta foto.",
  hair_roi_unreliable:
    "A área do cabelo não pôde ser delimitada com segurança nesta foto.",
  hair_roi_empty:
    "A área segura de edição do cabelo ficou vazia nesta foto.",
  hair_roi_coverage_out_of_range:
    "A área detectada para o cabelo ficou fora dos limites seguros para edição.",
  protected_region_in_mask:
    "A máscara tocou uma região protegida do rosto; a simulação foi bloqueada.",
  beard_region_not_allowed:
    "A máscara atingiu a barba. Como esta etapa altera somente cabelo, a prévia foi bloqueada.",
  background_lock_not_confirmed:
    "Não foi possível garantir que o fundo ficaria intacto.",
  identity_lock_failed:
    "A imagem gerada não preservou a identidade com confiança suficiente e foi descartada.",
  provider_rate_limited:
    "O serviço de geração está temporariamente no limite. Tente novamente mais tarde.",
  provider_timeout:
    "A geração demorou além do limite seguro. Nenhuma nova tentativa automática foi feita.",
  provider_unavailable:
    "O serviço de geração está temporariamente indisponível.",
  provider_request_failed:
    "O serviço de geração não conseguiu concluir a prévia.",
  provider_auth_failed:
    "O serviço de geração precisa de uma configuração do servidor.",
  provider_empty_output:
    "O serviço de geração não devolveu uma imagem válida.",
  provider_invalid_output:
    "A imagem devolvida pelo serviço não passou pela validação técnica.",
  simulation_pipeline_error:
    "A prévia foi interrompida por uma proteção técnica e sua foto original foi mantida.",
  simulation_in_progress:
    "Esta prévia já está sendo gerada. Ela aparecerá aqui assim que estiver disponível.",
  simulation_budget_exhausted:
    "O limite temporário de gerações desta análise foi atingido para proteger o consumo. As prévias já salvas continuam disponíveis.",
};

const SIMULATION_POLL_INTERVAL_MS = 3000;
const SIMULATION_POLL_MAX_ATTEMPTS = 40;

function simulationMessage(reason: string | null) {
  if (!reason) return "A simulação foi bloqueada com segurança e a foto original foi preservada.";
  return (
    SIMULATION_REASON_COPY[reason] ||
    "A simulação não passou por todas as validações de segurança. Sua foto original foi preservada."
  );
}

export function VisagismResultView({ result, analysisId, onReset }: Props) {
  const interpretation = result.interpretation;
  const rawHaircuts = useMemo(
    () =>
      Array.from(
        new Set(
          (result.recommended_hairstyles || []).filter(
            (item): item is string => typeof item === "string" && item.trim().length > 0
          )
        )
      ),
    [result.recommended_hairstyles]
  );
  const primaryName =
    interpretation?.primary_recommendation?.name ||
    result.primary_hairstyle ||
    rawHaircuts[0] ||
    null;

  const [selectedHaircut, setSelectedHaircut] = useState<string | null>(primaryName);
  const [simulations, setSimulations] = useState<Record<string, SimulationPreflightResult>>({});
  const [simulationLoading, setSimulationLoading] = useState<string | null>(null);
  const [simulationPolling, setSimulationPolling] = useState<string | null>(null);
  const [simulationError, setSimulationError] = useState("");
  const [selectedBarberBrief, setSelectedBarberBrief] = useState<BarberBrief | null>(
    interpretation?.barber_brief || null
  );
  const [previewMode, setPreviewMode] = useState<PreviewMode>("simulation");

  const selectedSimulation = selectedHaircut ? simulations[selectedHaircut] : undefined;

  useEffect(() => {
    if (!analysisId) return;
    let active = true;

    analysisApi
      .listVisagismSimulations(analysisId)
      .then((response) => {
        if (!active) return;
        const items = (response.data?.data || []) as SimulationPreflightResult[];
        const recovered: Record<string, SimulationPreflightResult> = {};
        for (const item of items) {
          if (item?.selected_haircut && item.simulation_status === "ready") {
            recovered[item.selected_haircut] = item;
          }
        }
        setSimulations((current) => ({ ...current, ...recovered }));
      })
      .catch(() => {
        // Cache recovery is optional; the result itself must remain usable.
      });

    return () => {
      active = false;
    };
  }, [analysisId]);

  useEffect(() => {
    if (!analysisId || !selectedHaircut || simulationPolling) return;
    let active = true;
    const cachedBrief = simulations[selectedHaircut]?.barber_brief;
    if (cachedBrief) {
      setSelectedBarberBrief(cachedBrief);
    } else if (selectedHaircut === primaryName && interpretation?.barber_brief) {
      setSelectedBarberBrief(interpretation.barber_brief);
    }

    analysisApi
      .getVisagismBarberBrief(analysisId, selectedHaircut)
      .then((response) => {
        if (!active) return;
        setSelectedBarberBrief((response.data?.data || null) as BarberBrief | null);
      })
      .catch(() => {
        // Keep the latest grounded brief already available in the result.
      });

    return () => {
      active = false;
    };
  }, [analysisId, interpretation?.barber_brief, primaryName, selectedHaircut, simulations]);

  const refreshCachedSimulations = async () => {
    if (!analysisId) return;
    try {
      const response = await analysisApi.listVisagismSimulations(analysisId);
      const items = (response.data?.data || []) as SimulationPreflightResult[];
      const recovered: Record<string, SimulationPreflightResult> = {};
      for (const item of items) {
        if (item?.selected_haircut && item.simulation_status === "ready") {
          recovered[item.selected_haircut] = item;
        }
      }
      setSimulations((current) => ({ ...current, ...recovered }));
    } catch {
      // Manual generation can still be used if cache refresh fails.
    }
  };

  const pollForSimulation = async (haircutName: string) => {
    if (!analysisId || simulationPolling) return;
    setSimulationPolling(haircutName);
    try {
      for (let attempt = 0; attempt < SIMULATION_POLL_MAX_ATTEMPTS; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, SIMULATION_POLL_INTERVAL_MS));
        const response = await analysisApi.listVisagismSimulations(analysisId);
        const items = (response.data?.data || []) as SimulationPreflightResult[];
        const ready = items.find(
          (item) => item?.selected_haircut === haircutName && item.simulation_status === "ready"
        );
        if (ready) {
          setSimulations((current) => ({ ...current, [haircutName]: ready }));
          if (ready.barber_brief) setSelectedBarberBrief(ready.barber_brief);
          setPreviewMode("simulation");
          setSimulationError("");
          return;
        }
      }
      setSimulationError(
        "A prévia continua processando no servidor. Você pode sair e reabrir esta análise mais tarde sem iniciar outra geração."
      );
    } catch {
      setSimulationError(
        "Não foi possível consultar a geração agora. Evite gerar novamente; reabra esta análise em alguns instantes."
      );
    } finally {
      setSimulationPolling(null);
    }
  };

  const chooseHaircut = (haircutName: string) => {
    setSelectedHaircut(haircutName);
    setSimulationError("");
    setPreviewMode(simulations[haircutName]?.simulation_status === "ready" ? "simulation" : "original");
  };

  const runSimulation = async () => {
    if (!analysisId || !selectedHaircut) return;
    const cached = simulations[selectedHaircut];
    if (cached?.simulation_status === "ready") {
      setPreviewMode("simulation");
      return;
    }

    setSimulationLoading(selectedHaircut);
    setSimulationError("");
    try {
      const response = await analysisApi.simulateVisagism(analysisId, selectedHaircut);
      const data = response.data?.data as SimulationPreflightResult;
      setSimulations((current) => ({ ...current, [selectedHaircut]: data }));
      if (data.barber_brief) setSelectedBarberBrief(data.barber_brief);
      if (data.simulation_status === "ready") {
        setPreviewMode("simulation");
      } else if (data.simulation_status === "processing") {
        void pollForSimulation(selectedHaircut);
      } else {
        setPreviewMode("original");
      }
    } catch (error) {
      const message =
        typeof error === "object" && error && "response" in error
          ? String(
              (error as { response?: { data?: { detail?: string; message?: string } } }).response
                ?.data?.detail ||
                (error as { response?: { data?: { detail?: string; message?: string } } }).response
                  ?.data?.message ||
                ""
            )
          : "";
      if (!message && selectedHaircut) {
        setSimulationError(
          "A conexão caiu durante a geração. Estou consultando o resultado salvo sem repetir a solicitação paga."
        );
        void pollForSimulation(selectedHaircut);
      } else {
        setSimulationError(
          message || "Não foi possível solicitar a simulação agora. Sua análise e foto original continuam preservadas."
        );
      }
    } finally {
      setSimulationLoading(null);
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
              {interpretation.current_hair_assessment.attention_points.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <Button className="mt-auto h-12 w-full" onClick={onReset}>
          Tentar novamente
        </Button>
      </main>
    );
  }

  const primary = interpretation?.primary_recommendation;
  const alternatives = interpretation?.alternative_hairstyles || [];

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-4 pb-8 pt-6">
      <p className="text-sm font-medium text-muted-foreground">Resultado</p>
      <h1 className="mt-1 text-2xl font-semibold">Sua análise foi concluída</h1>
      {interpretation?.executive_summary ? (
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{interpretation.executive_summary}</p>
      ) : null}

      {primaryName ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Recomendação principal
          </p>
          <h2 className="mt-2 text-xl font-semibold">{primaryName}</h2>
          {primary?.why_it_works ? (
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{primary.why_it_works}</p>
          ) : null}
          {primary?.professional_positioning ? (
            <p className="mt-3 text-sm leading-6">{primary.professional_positioning}</p>
          ) : null}
        </section>
      ) : (
        <div className="mt-6 rounded-xl border bg-muted/30 p-4 text-sm text-muted-foreground">
          Não houve dados suficientes para uma recomendação principal nesta sessão.
        </div>
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

      {analysisId && rawHaircuts.length ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Simulação visual
          </p>
          <h2 className="mt-2 text-lg font-semibold">Escolha um corte</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            A imagem só é gerada quando você pedir. Cortes já simulados são recuperados sem uma nova geração.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {rawHaircuts.map((haircut) => {
              const isSelected = haircut === selectedHaircut;
              const isCached = simulations[haircut]?.simulation_status === "ready";
              return (
                <button
                  key={haircut}
                  type="button"
                  onClick={() => chooseHaircut(haircut)}
                  className={`rounded-full border px-3 py-2 text-left text-xs font-medium transition-colors ${
                    isSelected ? "bg-foreground text-background" : "bg-background"
                  }`}
                  aria-pressed={isSelected}
                >
                  {haircut}{isCached ? " · salva" : ""}
                </button>
              );
            })}
          </div>

          {selectedHaircut ? (
            <div className="mt-5">
              <p className="text-sm font-medium">{selectedHaircut}</p>
              <Button
                variant="outline"
                className="mt-3 h-12 w-full"
                onClick={runSimulation}
                disabled={simulationLoading !== null || simulationPolling !== null}
              >
                {simulationLoading === selectedHaircut
                  ? "Gerando prévia segura..."
                  : simulationPolling === selectedHaircut
                    ? "Finalizando prévia..."
                  : selectedSimulation?.simulation_status === "ready"
                    ? "Ver prévia salva"
                    : "Gerar prévia deste corte"}
              </Button>
            </div>
          ) : null}

          {simulationError ? (
            <p className="mt-3 text-sm leading-6 text-destructive">{simulationError}</p>
          ) : null}

          {selectedSimulation ? (
            <div className="mt-5 rounded-xl border bg-muted/20 p-3">
              {selectedSimulation.simulation_status === "ready" ? (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                        previewMode === "original" ? "bg-foreground text-background" : "bg-background"
                      }`}
                      onClick={() => setPreviewMode("original")}
                    >
                      Original
                    </button>
                    <button
                      type="button"
                      className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                        previewMode === "simulation" ? "bg-foreground text-background" : "bg-background"
                      }`}
                      onClick={() => setPreviewMode("simulation")}
                    >
                      Simulação
                    </button>
                  </div>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={
                      previewMode === "original"
                        ? selectedSimulation.card_media.personPhoto
                        : selectedSimulation.card_media.displayImage
                    }
                    alt={
                      previewMode === "original"
                        ? "Foto original"
                        : `Simulação visual do corte ${selectedHaircut || "selecionado"}`
                    }
                    className="mt-3 w-full rounded-xl object-cover"
                  />
                  <p className="mt-3 text-sm font-medium">
                    {selectedSimulation.cached ? "Prévia salva recuperada" : "Prévia concluída"}
                  </p>
                </>
              ) : selectedSimulation.simulation_status === "processing" ? (
                <>
                  <p className="text-sm font-medium">Prévia em processamento</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {simulationMessage(selectedSimulation.reason)}
                  </p>
                  <Button
                    variant="outline"
                    className="mt-3 h-10 w-full"
                    onClick={() => void refreshCachedSimulations()}
                  >
                    Atualizar prévia
                  </Button>
                </>
              ) : (
                <>
                  {selectedSimulation.card_media?.displayImage ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={selectedSimulation.card_media.displayImage}
                      alt="Foto original preservada"
                      className="w-full rounded-xl object-cover"
                    />
                  ) : null}
                  <p className="mt-3 text-sm font-medium">Simulação bloqueada com segurança</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {simulationMessage(selectedSimulation.reason)}
                  </p>
                </>
              )}
            </div>
          ) : null}

          <p className="mt-4 text-xs leading-5 text-muted-foreground">
            A simulação é uma prévia visual. O resultado real pode variar conforme comprimento, textura, densidade e execução do corte.
          </p>
        </section>
      ) : null}

      {selectedBarberBrief ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Card do barbeiro
          </p>
          <h2 className="mt-2 text-lg font-semibold">
            {selectedBarberBrief.recommendation_name || selectedHaircut || primaryName || "Corte recomendado"}
          </h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div><dt className="font-medium">Topo</dt><dd className="text-muted-foreground">{selectedBarberBrief.top}</dd></div>
            <div><dt className="font-medium">Laterais</dt><dd className="text-muted-foreground">{selectedBarberBrief.sides}</dd></div>
            <div><dt className="font-medium">Parte de trás</dt><dd className="text-muted-foreground">{selectedBarberBrief.back}</dd></div>
            <div><dt className="font-medium">Franja</dt><dd className="text-muted-foreground">{selectedBarberBrief.fringe}</dd></div>
            <div><dt className="font-medium">Textura</dt><dd className="text-muted-foreground">{selectedBarberBrief.texture}</dd></div>
            <div><dt className="font-medium">Acabamento</dt><dd className="text-muted-foreground">{selectedBarberBrief.finish}</dd></div>
          </dl>
          <p className="mt-4 text-xs leading-5 text-muted-foreground">{selectedBarberBrief.note}</p>
        </section>
      ) : null}

      {interpretation?.current_hair_assessment ? (
        <section className="mt-6 rounded-2xl border bg-card p-5">
          <h2 className="font-semibold">Seu cabelo hoje</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {interpretation.current_hair_assessment.summary}
          </p>
          {interpretation.current_hair_assessment.attention_points.length ? (
            <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
              {interpretation.current_hair_assessment.attention_points.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {interpretation?.confidence_note ? (
        <p className="mt-5 text-xs leading-5 text-muted-foreground">{interpretation.confidence_note}</p>
      ) : null}

      <div className="mt-auto pt-8">
        <Button variant="outline" className="h-12 w-full" onClick={onReset}>
          Fazer nova análise
        </Button>
      </div>
    </main>
  );
}
