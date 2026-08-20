"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, Share2, Sparkles } from "lucide-react";
import { useVisagismResult } from "@/hooks/use-visagism";

export default function VisagismResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const analysisId = params.id;
  const { data, isLoading, isError } = useVisagismResult(analysisId);
  const [cardFailed, setCardFailed] = useState(false);
  const [shareMessage, setShareMessage] = useState<string | null>(null);

  const shareCard = async () => {
    if (!data?.card_url) return;
    setShareMessage(null);
    try {
      if (navigator.share) {
        await navigator.share({
          title: "Card de Visagismo Vision",
          text: data.top_recommendation?.name || "Recomendação de corte",
          url: data.card_url,
        });
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
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <h1 className="text-3xl font-bold tracking-tight">Visagismo</h1>
            </div>
            <p className="text-muted-foreground">Análise facial e recomendações de corte baseadas nas fotos do ensaio.</p>
          </div>
          {data?.status && <Badge>{data.status}</Badge>}
        </div>

        {(isLoading || !data) && !isError && (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="font-medium">Processando sua análise...</p>
              <p className="mt-2 text-sm text-muted-foreground">O Vision está selecionando as melhores vistas, medindo o rosto e ranqueando os cortes.</p>
            </CardContent>
          </Card>
        )}

        {isError && (
          <Card>
            <CardContent className="py-10 text-center text-destructive">Não foi possível consultar o resultado desta análise.</CardContent>
          </Card>
        )}

        {data?.status === "failed" && (
          <Card>
            <CardContent className="py-10 text-center text-destructive">A análise falhou. Volte ao ensaio, confira as fotos e tente novamente.</CardContent>
          </Card>
        )}

        {data && data.status !== "failed" && (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader><CardTitle className="text-base">Fotos processadas</CardTitle></CardHeader>
                <CardContent><p className="text-3xl font-bold">{data.processed_images}</p></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-base">Formato facial</CardTitle></CardHeader>
                <CardContent><p className="text-lg font-semibold">{String(data.face_shape?.value || "Não determinado")}</p></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-base">Fontes reais</CardTitle></CardHeader>
                <CardContent><p className="text-sm text-muted-foreground">{data.analysis_sources.join(", ") || "Não informado"}</p></CardContent>
              </Card>
            </div>

            {data.top_recommendation && (
              <Card className="border-primary/40">
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle>Recomendação principal: {data.top_recommendation.name}</CardTitle>
                    <Badge>{Math.round(data.top_recommendation.compatibility_score * 100)}%</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p><strong>Topo:</strong> {data.top_recommendation.top_cm.join("–")} cm</p>
                  <p><strong>Laterais:</strong> {data.top_recommendation.sides_mm.join("–")} mm</p>
                  <p><strong>Degradê:</strong> {data.top_recommendation.fade}</p>
                  <p><strong>Direção:</strong> {data.top_recommendation.direction}</p>
                  <p><strong>Acabamento:</strong> {data.top_recommendation.finish}</p>
                  {data.top_recommendation.reasons.length > 0 && (
                    <p><strong>Por quê:</strong> {data.top_recommendation.reasons.join(" ")}</p>
                  )}
                  <p><strong>Evitar:</strong> {data.top_recommendation.avoid}</p>
                </CardContent>
              </Card>
            )}

            <section className="space-y-3">
              <h2 className="text-xl font-semibold">5 cortes ranqueados</h2>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data.recommendations.map((cut) => (
                  <Card key={`${cut.rank}-${cut.key}`}>
                    <CardHeader>
                      <div className="flex items-center justify-between gap-2">
                        <CardTitle className="text-lg">#{cut.rank} {cut.name}</CardTitle>
                        <Badge variant="secondary">{Math.round(cut.compatibility_score * 100)}%</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <p><strong>Topo:</strong> {cut.top_cm.join("–")} cm</p>
                      <p><strong>Laterais:</strong> {cut.sides_mm.join("–")} mm</p>
                      <p><strong>Manutenção:</strong> {cut.maintenance}</p>
                      {cut.reasons[0] && <p className="text-muted-foreground">{cut.reasons[0]}</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>

            {data.card_url && (
              <Card>
                <CardHeader><CardTitle>Card para o barbeiro</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  {!cardFailed ? (
                    <img
                      src={data.card_url}
                      alt="Card visual de visagismo para o barbeiro"
                      onError={() => setCardFailed(true)}
                      className="mx-auto max-h-[720px] w-auto max-w-full rounded-lg border"
                    />
                  ) : (
                    <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
                      O card foi gerado, mas não foi possível carregar a imagem agora. Use o botão abaixo para abrir o arquivo diretamente.
                    </div>
                  )}
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button asChild>
                      <a href={data.card_url} target="_blank" rel="noreferrer">
                        <Download className="mr-2 h-4 w-4" /> Abrir / baixar card
                      </a>
                    </Button>
                    <Button variant="outline" onClick={shareCard}>
                      <Share2 className="mr-2 h-4 w-4" /> Compartilhar
                    </Button>
                  </div>
                  {shareMessage && <p className="text-sm text-muted-foreground">{shareMessage}</p>}
                </CardContent>
              </Card>
            )}

            {data.limitations.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="text-base">Limitações da análise</CardTitle></CardHeader>
                <CardContent>
                  <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {data.limitations.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </CardContent>
              </Card>
            )}

            <Button variant="outline" onClick={() => router.push("/photoshoots")}>Voltar aos ensaios</Button>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
