"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, Share2, Sparkles } from "lucide-react";
import { useVisagismResult } from "@/hooks/use-visagism";

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Não informado";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(renderValue).join(", ");
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${labelize(key)}: ${renderValue(item)}`)
      .join(" · ");
  }
  return String(value);
}

function getSelectedViewUrl(selectedViews: Record<string, unknown>): string | null {
  const preferredKeys = ["frontal", "front", "hairline", "three_quarter_right", "three_quarter_left"];
  for (const key of preferredKeys) {
    const candidate = selectedViews[key];
    if (!candidate || typeof candidate !== "object") continue;
    const record = candidate as Record<string, unknown>;
    const url = record.url;
    if (typeof url === "string" && url.startsWith("http")) return url;
  }
  return null;
}

function EvidenceCard({ title, data }: { title: string; data: Record<string, unknown> }) {
  const entries = Object.entries(data || {});
  if (!entries.length) return null;
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent className="space-y-3 text-sm">
        {entries.map(([key, value]) => (
          <div key={key} className="grid gap-1 border-b pb-2 last:border-0 last:pb-0 sm:grid-cols-[180px_1fr]">
            <span className="font-medium">{labelize(key)}</span>
            <span className="break-words text-muted-foreground">{renderValue(value)}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function VisagismResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const analysisId = params.id;
  const { data, isLoading, isError } = useVisagismResult(analysisId);
  const [cardFailed, setCardFailed] = useState(false);
  const [shareMessage, setShareMessage] = useState<string | null>(null);

  const originalImageUrl = data ? getSelectedViewUrl(data.selected_views) : null;

  const shareCard = async () => {
    if (!data?.card_url) return;
    setShareMessage(null);
    try {
      if (navigator.share) {
        await navigator.share({ title: "Card de Visagismo Vision", text: data.top_recommendation?.name || "Recomendação de corte", url: data.card_url });
        setShareMessage("Card compartilhado.");
        return;
      }
      await navigator.clipboard.writeText(data.card_url);
      setShareMessage("Link do card copiado.");
    } catch {
      setShareMessage("Não foi possível compartilhar o card neste dispositivo.");
    }
  };

  return (
    <DashboardShell>
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary" /><h1 className="text-3xl font-bold tracking-tight">Visagismo</h1></div>
            <p className="text-muted-foreground">Análise facial e recomendações de corte baseadas nas fotos do ensaio.</p>
          </div>
          {data?.status && <Badge>{data.status}</Badge>}
        </div>

        {(isLoading || !data) && !isError && <Card><CardContent className="py-12 text-center"><p className="font-medium">Processando sua análise...</p><p className="mt-2 text-sm text-muted-foreground">O Vision está selecionando as melhores vistas, medindo o rosto e ranqueando os cortes.</p></CardContent></Card>}
        {isError && <Card><CardContent className="py-10 text-center text-destructive">Não foi possível consultar o resultado desta análise.</CardContent></Card>}
        {data?.status === "failed" && <Card><CardContent className="py-10 text-center text-destructive">A análise falhou. Volte ao ensaio, confira as fotos e tente novamente.</CardContent></Card>}

        {data && data.status !== "failed" && (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <Card><CardHeader><CardTitle className="text-base">Fotos processadas</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold">{data.processed_images}</p></CardContent></Card>
              <Card><CardHeader><CardTitle className="text-base">Formato facial</CardTitle></CardHeader><CardContent><p className="text-lg font-semibold">{String(data.face_shape?.value || "Não determinado")}</p></CardContent></Card>
              <Card><CardHeader><CardTitle className="text-base">Fontes reais</CardTitle></CardHeader><CardContent><p className="text-sm text-muted-foreground">{data.analysis_sources.join(", ") || "Não informado"}</p></CardContent></Card>
            </div>

            <section className="space-y-3">
              <div><h2 className="text-xl font-semibold">Evidências da análise</h2><p className="text-sm text-muted-foreground">Dados objetivos usados pelo Vision antes de recomendar os cortes.</p></div>
              <div className="grid gap-4 lg:grid-cols-3">
                <EvidenceCard title="Vistas selecionadas" data={data.selected_views} />
                <EvidenceCard title="Medições faciais" data={data.measurements} />
                <EvidenceCard title="Análise capilar" data={data.hair_analysis} />
              </div>
            </section>

            {data.top_recommendation && <Card className="border-primary/40"><CardHeader><div className="flex flex-wrap items-center justify-between gap-2"><CardTitle>Recomendação principal: {data.top_recommendation.name}</CardTitle><Badge>{Math.round(data.top_recommendation.compatibility_score * 100)}%</Badge></div></CardHeader><CardContent className="space-y-3 text-sm"><p><strong>Topo:</strong> {data.top_recommendation.top_cm.join("–")} cm</p><p><strong>Laterais:</strong> {data.top_recommendation.sides_mm.join("–")} mm</p><p><strong>Degradê:</strong> {data.top_recommendation.fade}</p><p><strong>Direção:</strong> {data.top_recommendation.direction}</p><p><strong>Acabamento:</strong> {data.top_recommendation.finish}</p>{data.top_recommendation.reasons.length > 0 && <p><strong>Por quê:</strong> {data.top_recommendation.reasons.join(" ")}</p>}<p><strong>Evitar:</strong> {data.top_recommendation.avoid}</p></CardContent></Card>}

            <section className="space-y-3"><h2 className="text-xl font-semibold">5 cortes ranqueados</h2><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{data.recommendations.map((cut) => <Card key={`${cut.rank}-${cut.key}`}><CardHeader><div className="flex items-center justify-between gap-2"><CardTitle className="text-lg">#{cut.rank} {cut.name}</CardTitle><Badge variant="secondary">{Math.round(cut.compatibility_score * 100)}%</Badge></div></CardHeader><CardContent className="space-y-2 text-sm"><p><strong>Topo:</strong> {cut.top_cm.join("–")} cm</p><p><strong>Laterais:</strong> {cut.sides_mm.join("–")} mm</p><p><strong>Manutenção:</strong> {cut.maintenance}</p>{cut.reasons[0] && <p className="text-muted-foreground">{cut.reasons[0]}</p>}</CardContent></Card>)}</div></section>

            {data.card_url && <Card><CardHeader><CardTitle>Card para o barbeiro</CardTitle></CardHeader><CardContent className="space-y-4">{!cardFailed ? <img src={data.card_url} alt="Card visual de visagismo para o barbeiro" onError={() => setCardFailed(true)} className="mx-auto max-h-[720px] w-auto max-w-full rounded-lg border" /> : <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">O card foi gerado, mas não foi possível carregar a imagem agora. Use o botão abaixo para abrir o arquivo diretamente.</div>}<div className="flex flex-col gap-2 sm:flex-row"><a href={data.card_url} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"><Download className="mr-2 h-4 w-4" /> Abrir / baixar card</a><Button variant="outline" onClick={shareCard}><Share2 className="mr-2 h-4 w-4" /> Compartilhar</Button></div>{shareMessage && <p className="text-sm text-muted-foreground">{shareMessage}</p>}</CardContent></Card>}

            {data.simulation_url && (
              <Card>
                <CardHeader><CardTitle>Simulação do corte</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {originalImageUrl && (
                      <div>
                        <p className="mb-2 text-sm text-muted-foreground">Antes</p>
                        <img src={originalImageUrl} alt="Foto original" className="aspect-[3/4] w-full rounded-lg border object-cover" />
                      </div>
                    )}
                    <div>
                      <p className="mb-2 text-sm text-muted-foreground">Depois (simulação)</p>
                      <img src={data.simulation_url} alt="Simulação do corte recomendado" className="aspect-[3/4] w-full rounded-lg border object-cover" />
                    </div>
                  </div>
                  {!originalImageUrl && <p className="text-xs text-muted-foreground">A foto original pública não está disponível neste resultado; exibindo apenas a simulação.</p>}
                  <p className="text-xs text-muted-foreground">Simulação gerada por IA. Resultado pode variar. Sempre consulte um profissional.</p>
                </CardContent>
              </Card>
            )}

            {data.limitations.length > 0 && <Card><CardHeader><CardTitle className="text-base">Limitações da análise</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></CardContent></Card>}
            <Button variant="outline" onClick={() => router.push("/photoshoots")}>Voltar aos ensaios</Button>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
