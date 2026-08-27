"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  PhotoUploadGuide,
  VisagismPhotoAngle,
  VisagismPhotoDraft,
} from "@/components/visagism/photo-upload-guide";
import { VisagismResultView } from "@/components/visagism/visagism-result";
import api, { analysisApi, photoApi, photoshootApi, profileApi } from "@/lib/api";
import {
  PersistedCompletedAnalysis,
  clearActiveAnalysis,
  getActiveAnalysis,
  getLastCompletedAnalysis,
  setActiveAnalysis,
  setLastCompletedAnalysis,
} from "@/lib/visagism-storage";
import type { Analysis, PhotoTriageResult, Profile, VisagismResult } from "@/types";

type Step = "landing" | "upload" | "review" | "processing" | "result" | "error";

type UploadedPhotoState = {
  photoId: string;
  triage: PhotoTriageResult;
};

type HistoryItem = {
  id: string;
  createdAt: string;
  confidenceScore?: number;
  faceShapeCategory?: string;
  primaryHairstyle?: string | null;
};

type AnalysisDetail = Analysis & {
  profile_id?: string;
  completed_at?: string;
};

type RecoverySource = "url" | "local_storage" | "history" | "polling_completion";

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

const backendAngle: Record<VisagismPhotoAngle, string> = {
  front: "front",
  three_quarter: "left_45",
  profile: "left_profile",
};

const faceShapeLabels: Record<string, string> = {
  round: "Redondo",
  redondo: "Redondo",
  oval: "Oval",
  square: "Quadrado",
  quadrado: "Quadrado",
  heart: "Coração",
  coracao: "Coração",
  coração: "Coração",
  diamond: "Diamante",
  diamante: "Diamante",
  oblong: "Oblongo",
  oblongo: "Oblongo",
  triangular: "Triangular",
  triangle: "Triangular",
};

function faceShapeLabel(value?: string) {
  if (!value) return undefined;
  return faceShapeLabels[value.toLowerCase()] || value;
}

function extractMessage(error: unknown): string {
  if (typeof error === "object" && error && "response" in error) {
    const response = (
      error as {
        response?: {
          data?: {
            detail?: string;
            message?: string;
          };
        };
      }
    ).response;

    const apiMessage = response?.data?.detail || response?.data?.message;
    if (apiMessage) return apiMessage;
  }

  if (error instanceof Error && error.message) return error.message;
  return "Não foi possível concluir esta etapa.";
}

function getStatusCode(error: unknown): number | undefined {
  if (typeof error !== "object" || !error || !("response" in error)) return undefined;
  return (error as { response?: { status?: number } }).response?.status;
}

function replaceAnalysisIdInUrl(analysisId: string | null) {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (analysisId) {
    url.searchParams.set("analysisId", analysisId);
  } else {
    url.searchParams.delete("analysisId");
  }
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

function logRecovery(event: string, data: Record<string, unknown>) {
  console.info(`[${event}]`, data);
}

export default function VisagismPage() {
  const [step, setStep] = useState<Step>("landing");
  const [photos, setPhotos] = useState<VisagismPhotoDraft[]>(initialPhotos);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploaded, setUploaded] = useState<Record<string, UploadedPhotoState>>({});
  const [activePhotoshootId, setActivePhotoshootId] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [result, setResult] = useState<VisagismResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [lastCompleted, setLastCompleted] = useState<PersistedCompletedAnalysis | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const selectedCount = useMemo(() => photos.filter((photo) => photo.file).length, [photos]);
  const allSelected = selectedCount === photos.length;
  const allTriaged = photos.every((photo) => uploaded[photo.angle]?.triage?.accepted);

  const showRecoveryError = useCallback((error: unknown) => {
    const status = getStatusCode(error);
    if (status === 404) {
      setErrorMessage("Análise não encontrada. Ela pode ter sido removida ou o link pode estar incorreto.");
    } else if (status === 401) {
      setErrorMessage("Sua sessão expirou. Entre novamente para acessar a análise.");
    } else if (status === 403) {
      setErrorMessage("Você não tem permissão para acessar esta análise.");
    } else {
      setErrorMessage(extractMessage(error));
    }
    setStep("error");
  }, []);

  const loadResult = useCallback(
    async (id: string, source: RecoverySource) => {
      try {
        const [analysisResponse, visagismResponse] = await Promise.all([
          api.get(`/api/v1/analyses/${id}`),
          analysisApi.getVisagism(id),
        ]);
        const analysisData = analysisResponse.data?.data as AnalysisDetail | undefined;
        const visagismData = (visagismResponse.data?.data || {}) as VisagismResult;

        setAnalysisId(id);
        setResult(visagismData);
        clearActiveAnalysis();
        replaceAnalysisIdInUrl(id);

        if (analysisData?.profile_id) {
          const parsedCompletedAt = analysisData.completed_at
            ? Date.parse(analysisData.completed_at)
            : Number.NaN;
          const persisted = setLastCompletedAnalysis({
            analysisId: id,
            profileId: analysisData.profile_id,
            completedAt: Number.isFinite(parsedCompletedAt) ? parsedCompletedAt : Date.now(),
            faceShapeCategory: visagismData.face_shape_category,
            primaryHairstyle: visagismData.primary_hairstyle,
            confidenceScore: analysisData.confidence_score,
          });
          setLastCompleted(persisted);
        }

        setStep("result");
        logRecovery("VISAGISM_RESULT_RECOVERY", {
          analysis_id: id,
          source,
          status: "completed",
        });
        return true;
      } catch (error) {
        clearActiveAnalysis();
        showRecoveryError(error);
        return false;
      }
    },
    [showRecoveryError]
  );

  const recoverAnalysis = useCallback(
    async (id: string, source: Exclude<RecoverySource, "polling_completion">) => {
      setAnalysisId(id);
      setErrorMessage("");
      setStep("processing");

      try {
        const response = await analysisApi.get(id);
        const status = response.data?.data?.status as string | undefined;

        if (status === "completed") {
          await loadResult(id, source);
          return;
        }

        if (status === "failed") {
          clearActiveAnalysis();
          setAnalysisId(null);
          setErrorMessage(
            (response.data?.data?.error_message as string | undefined) ||
              "A análise não foi concluída. Tente novamente com outras fotos."
          );
          setStep("error");
          return;
        }

        if (status === "processing" || status === "queued" || status === "pending") {
          setActiveAnalysis(id);
          logRecovery("VISAGISM_POLL_RECOVERED", {
            analysis_id: id,
            source,
            status,
          });
          return;
        }

        clearActiveAnalysis();
        setAnalysisId(null);
        setErrorMessage("O servidor retornou um estado de análise que não reconhecemos.");
        setStep("error");
      } catch (error) {
        clearActiveAnalysis();
        showRecoveryError(error);
      }
    },
    [loadResult, showRecoveryError]
  );

  useEffect(() => {
    setLastCompleted(getLastCompletedAnalysis());

    const url = new URL(window.location.href);
    const urlAnalysisId = url.searchParams.get("analysisId");
    if (urlAnalysisId) {
      void recoverAnalysis(urlAnalysisId, "url");
      return;
    }

    const active = getActiveAnalysis();
    if (active) {
      setAnalysisId(active.analysisId);
      setStep("processing");
      logRecovery("VISAGISM_POLL_RECOVERED", {
        analysis_id: active.analysisId,
        source: "local_storage",
        status: "resume",
      });
    }
  }, [recoverAnalysis]);

  useEffect(() => {
    let active = true;
    profileApi
      .list({ per_page: 100 })
      .then((response) => {
        if (!active) return;
        const data = (response.data?.data || []) as Profile[];
        setProfiles(data);
        if (data.length === 1) setSelectedProfileId(data[0].id);
      })
      .catch(() => {
        if (active) setErrorMessage("Não foi possível carregar seus perfis.");
      })
      .finally(() => {
        if (active) setIsLoadingProfiles(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (step !== "landing" || !selectedProfileId) return;

    let active = true;
    setIsLoadingHistory(true);

    const loadHistory = async () => {
      try {
        const response = await analysisApi.list({ profile_id: selectedProfileId });
        const analyses = ((response.data?.data || []) as Analysis[])
          .filter((analysis) => analysis.status === "completed")
          .sort(
            (a, b) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
          .slice(0, 5);

        const summaries = await Promise.all(
          analyses.map(async (analysis): Promise<HistoryItem> => {
            try {
              const visagismResponse = await analysisApi.getVisagism(analysis.id);
              const visagism = (visagismResponse.data?.data || {}) as VisagismResult;
              return {
                id: analysis.id,
                createdAt: analysis.created_at,
                confidenceScore: analysis.confidence_score,
                faceShapeCategory: visagism.face_shape_category,
                primaryHairstyle: visagism.primary_hairstyle,
              };
            } catch {
              return {
                id: analysis.id,
                createdAt: analysis.created_at,
                confidenceScore: analysis.confidence_score,
              };
            }
          })
        );

        if (active) setHistory(summaries);
      } catch {
        if (active) setHistory([]);
      } finally {
        if (active) setIsLoadingHistory(false);
      }
    };

    void loadHistory();
    return () => {
      active = false;
    };
  }, [selectedProfileId, step]);

  useEffect(() => {
    if (step !== "processing" || !analysisId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const response = await analysisApi.get(analysisId);
        if (cancelled) return;
        const status = response.data?.data?.status as string | undefined;

        if (status === "completed") {
          await loadResult(analysisId, "polling_completion");
          return;
        }

        if (status === "failed") {
          clearActiveAnalysis();
          setAnalysisId(null);
          setErrorMessage(
            (response.data?.data?.error_message as string | undefined) ||
              "A análise não foi concluída. Tente novamente com outras fotos."
          );
          setStep("error");
          return;
        }

        timer = setTimeout(poll, 2000);
      } catch (error) {
        if (cancelled) return;
        if (getStatusCode(error) === 409) {
          clearActiveAnalysis();
          setAnalysisId(null);
          setErrorMessage(extractMessage(error));
          setStep("error");
          return;
        }

        clearActiveAnalysis();
        showRecoveryError(error);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [analysisId, loadResult, showRecoveryError, step]);

  const handlePhotoChange = (angle: VisagismPhotoAngle, file: File) => {
    setUploaded((current) => {
      const next = { ...current };
      delete next[angle];
      return next;
    });
    setActivePhotoshootId(null);
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

  const handleRetake = (angle: VisagismPhotoAngle) => {
    setUploaded((current) => {
      const next = { ...current };
      delete next[angle];
      return next;
    });
    setActivePhotoshootId(null);
    setPhotos((current) =>
      current.map((photo) => {
        if (photo.angle !== angle) return photo;
        if (photo.previewUrl) URL.revokeObjectURL(photo.previewUrl);
        return {
          ...photo,
          file: undefined,
          previewUrl: undefined,
        };
      })
    );
  };

  const uploadAndTriage = async () => {
    if (!selectedProfileId || !allSelected) return;
    setIsSubmitting(true);
    setErrorMessage("");
    setUploaded({});
    setActivePhotoshootId(null);

    try {
      const shootResponse = await photoshootApi.create({
        profile_id: selectedProfileId,
        title: `Visagismo mobile ${new Date().toLocaleDateString("pt-BR")}`,
        type: "update",
        notes: "Fluxo mobile de visagismo",
      });
      const photoshootId = shootResponse.data?.data?.id as string;
      if (!photoshootId) throw new Error("ID da sessão de fotos não retornado pelo servidor.");

      for (const photo of photos) {
        if (!photo.file) continue;
        const uploadResponse = await photoshootApi.uploadPhoto(
          photoshootId,
          photo.file,
          backendAngle[photo.angle]
        );
        const photoId = uploadResponse.data?.data?.id as string;
        if (!photoId) throw new Error(`ID da foto ${photo.label} não retornado após upload.`);

        const triageResponse = await photoApi.triage(photoId);
        const triage = triageResponse.data?.data as PhotoTriageResult;
        setUploaded((current) => ({
          ...current,
          [photo.angle]: { photoId, triage },
        }));
      }

      setActivePhotoshootId(photoshootId);
    } catch (error) {
      setErrorMessage(extractMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const startAnalysis = async () => {
    if (!activePhotoshootId || !allTriaged) return;
    setIsSubmitting(true);
    setErrorMessage("");
    replaceAnalysisIdInUrl(null);

    try {
      const analysisResponse = await analysisApi.start(activePhotoshootId, {
        analysis_types: ["facial", "grooming", "colorimetry", "photogenic", "expressions", "visagism"],
        priority: "normal",
        notify_on_complete: true,
      });
      const newAnalysisId = analysisResponse.data?.data?.analysis_id as string;
      if (!newAnalysisId) throw new Error("ID da análise não retornado pelo servidor.");

      setActiveAnalysis(newAnalysisId);
      setAnalysisId(newAnalysisId);
      setStep("processing");
    } catch (error) {
      setErrorMessage(extractMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetFlow = () => {
    clearActiveAnalysis();
    replaceAnalysisIdInUrl(null);
    setStep("upload");
    setPhotos(initialPhotos.map((photo) => ({ ...photo })));
    setUploaded({});
    setActivePhotoshootId(null);
    setAnalysisId(null);
    setResult(null);
    setErrorMessage("");
  };

  const openLastCompleted = () => {
    if (!lastCompleted) return;
    void recoverAnalysis(lastCompleted.analysisId, "local_storage");
  };

  const openHistoryItem = (id: string) => {
    void recoverAnalysis(id, "history");
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
          disabled={isSubmitting}
        >
          ← Voltar
        </button>

        <div>
          <p className="text-sm font-medium text-muted-foreground">Revisão</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Confira suas fotos</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Primeiro enviamos e validamos as três fotos. A análise só é liberada quando todas estiverem aprovadas.
          </p>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          {photos.map((photo, index) => {
            const triage = uploaded[photo.angle]?.triage;
            const isRejected = triage && !triage.accepted;
            return (
              <article key={photo.angle} className="overflow-hidden rounded-xl border bg-card">
                {photo.previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={photo.previewUrl} alt={photo.label} className="aspect-[4/3] w-full object-cover" />
                ) : (
                  <div className="flex aspect-[4/3] items-center justify-center bg-muted text-xs text-muted-foreground">Sem foto</div>
                )}
                <div className="p-3">
                  <p className="text-xs text-muted-foreground">Foto {index + 1}</p>
                  <p className="font-medium">{photo.label}</p>
                  <p className={`mt-1 text-xs ${isRejected ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                    {!triage ? "Aguardando triagem" : triage.accepted ? "✓ Foto aceita" : `⚠ ${triage.rejection_reasons?.[0] || "Foto rejeitada"}`}
                  </p>
                  {isRejected && (
                    <button
                      type="button"
                      onClick={() => handleRetake(photo.angle)}
                      className="mt-2 text-xs font-medium text-primary hover:underline"
                      disabled={isSubmitting}
                    >
                      ↻ Refazer esta foto
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>

        {errorMessage ? (
          <div className="mt-4 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{errorMessage}</div>
        ) : null}

        <div className="mt-auto pt-8">
          {Object.keys(uploaded).length > 0 && !allTriaged && !isSubmitting ? (
            <div className="mb-3 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
              Aguarde as três triagens. Se alguma foto for rejeitada, refaça apenas aquela foto.
            </div>
          ) : null}

          {allTriaged && activePhotoshootId ? (
            <Button className="h-12 w-full text-base" disabled={isSubmitting} onClick={startAnalysis}>
              {isSubmitting ? "Iniciando análise..." : "Iniciar análise"}
            </Button>
          ) : (
            <Button className="h-12 w-full text-base" disabled={!allSelected || isSubmitting} onClick={uploadAndTriage}>
              {isSubmitting ? "Enviando e validando..." : "Enviar fotos para triagem"}
            </Button>
          )}
        </div>
      </main>
    );
  }

  if (step === "processing") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col items-center justify-center bg-background px-6 text-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-muted border-t-primary" aria-hidden="true" />
        <h1 className="mt-6 text-2xl font-semibold">Analisando suas fotos</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">Estamos verificando rosto, cabelo, proporções e recomendações. Esta tela atualiza automaticamente.</p>
        {analysisId ? <p className="mt-6 text-xs text-muted-foreground">Análise {analysisId.slice(0, 8)}</p> : null}
      </main>
    );
  }

  if (step === "result" && result) {
    return <VisagismResultView result={result} analysisId={analysisId} onReset={resetFlow} />;
  }

  if (step === "error") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col items-center justify-center bg-background px-6 text-center">
        <h1 className="text-2xl font-semibold">Não foi possível concluir</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{errorMessage}</p>
        <Button className="mt-7 h-12 w-full" onClick={resetFlow}>Começar uma nova análise</Button>
      </main>
    );
  }

  const visibleLastCompleted =
    lastCompleted && selectedProfileId && lastCompleted.profileId === selectedProfileId
      ? lastCompleted
      : null;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-5 pb-8 pt-10">
      <div className="flex flex-1 flex-col justify-center">
        <div className="mb-7 flex h-20 w-20 items-center justify-center rounded-3xl border bg-muted text-3xl" aria-hidden="true">✂️</div>

        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Vision</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Descubra o corte que valoriza seu rosto</h1>
        <p className="mt-4 text-base leading-7 text-muted-foreground">Envie três fotos e receba uma análise baseada nas características reais do seu rosto e cabelo.</p>

        <div className="mt-7 space-y-3 rounded-2xl border bg-card p-4 text-sm">
          <div className="flex items-center gap-3"><span className="font-semibold">1.</span><span>Frontal</span></div>
          <div className="flex items-center gap-3"><span className="font-semibold">2.</span><span>3/4</span></div>
          <div className="flex items-center gap-3"><span className="font-semibold">3.</span><span>Perfil</span></div>
        </div>

        <label className="mt-5 text-sm font-medium" htmlFor="profile">Perfil da análise</label>
        <select
          id="profile"
          className="mt-2 h-12 rounded-md border bg-background px-3 text-sm"
          value={selectedProfileId}
          onChange={(event) => setSelectedProfileId(event.target.value)}
          disabled={isLoadingProfiles}
        >
          <option value="">{isLoadingProfiles ? "Carregando perfis..." : "Selecione um perfil"}</option>
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>{profile.artistic_name || profile.full_name}</option>
          ))}
        </select>

        {!isLoadingProfiles && profiles.length === 0 ? (
          <p className="mt-2 text-sm text-destructive">É necessário ter um perfil cadastrado antes de iniciar.</p>
        ) : null}

        {visibleLastCompleted ? (
          <section className="mt-6 rounded-2xl border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Última análise</p>
            <p className="mt-2 text-sm font-medium">
              {faceShapeLabel(visibleLastCompleted.faceShapeCategory)
                ? `Rosto: ${faceShapeLabel(visibleLastCompleted.faceShapeCategory)}`
                : "Análise concluída"}
            </p>
            {visibleLastCompleted.primaryHairstyle ? (
              <p className="mt-1 text-sm text-muted-foreground">Corte: {visibleLastCompleted.primaryHairstyle}</p>
            ) : null}
            <p className="mt-1 text-xs text-muted-foreground">
              {new Date(visibleLastCompleted.completedAt).toLocaleDateString("pt-BR")}
            </p>
            <Button variant="outline" className="mt-3 h-10 w-full" onClick={openLastCompleted}>
              Ver última análise
            </Button>
          </section>
        ) : null}

        {selectedProfileId ? (
          <section className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Análises anteriores</p>
            {isLoadingHistory ? (
              <p className="mt-3 text-sm text-muted-foreground">Carregando histórico...</p>
            ) : history.length > 0 ? (
              <div className="mt-3 space-y-2">
                {history.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => openHistoryItem(item.id)}
                    className="flex w-full items-center justify-between gap-3 rounded-xl border bg-card p-3 text-left transition-colors hover:bg-muted/30"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {faceShapeLabel(item.faceShapeCategory)
                          ? `Rosto ${faceShapeLabel(item.faceShapeCategory)}`
                          : "Análise concluída"}
                      </p>
                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {new Date(item.createdAt).toLocaleDateString("pt-BR")}
                        {item.primaryHairstyle ? ` · ${item.primaryHairstyle}` : ""}
                        {typeof item.confidenceScore === "number"
                          ? ` · ${Math.round(item.confidenceScore * 100)}%`
                          : ""}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs font-medium text-primary">Ver →</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">Nenhuma análise concluída neste perfil ainda.</p>
            )}
          </section>
        ) : null}
      </div>

      <div className="pt-8">
        <Button className="h-12 w-full text-base" onClick={() => setStep("upload")} disabled={!selectedProfileId}>Começar nova análise</Button>
        <p className="mt-3 text-center text-xs text-muted-foreground">Fotos → triagem → análise → resultado</p>
      </div>
    </main>
  );
}
