"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { analysisApi } from "@/lib/api";
import { Analysis } from "@/types";

export default function AnalysisDetailPage() {
  const params = useParams<{ id: string }>();
  const analysisId = params.id;

  const { data: analysis, isLoading } = useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: async () => {
      const response = await analysisApi.get(analysisId);
      return response.data.data as Analysis;
    },
    enabled: Boolean(analysisId),
  });

  if (isLoading || !analysis) {
    return (
      <DashboardShell>
        <div className="py-12 text-center text-muted-foreground">Carregando análise...</div>
      </DashboardShell>
    );
  }

  const visagism = analysis.visagism || {};
  const userFacing = visagism.user_facing_result || {};
  const visual = userFacing.visual_simulation || {};
  const primary = userFacing.primary_recommendation;
  const recommendations = userFacing.recommendations || [];

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Resultado de Visagismo</h1>
            <p className="text-muted-foreground">Análise #{analysis.id.slice(0, 8)}</p>
          </div>
          <Link
            href="/analyses"
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            Voltar
          </Link>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant={userFacing.complete ? "default" : "secondary"}>
            {userFacing.complete ? "Resultado completo" : "Resultado visual pendente"}
          </Badge>
          {userFacing.face_shape && (
            <Badge variant="outline">Rosto: {userFacing.face_shape}</Badge>
          )}
          {analysis.confidence_score !== undefined && (
            <Badge variant="outline">
              Confiança: {(analysis.confidence_score * 100).toFixed(0)}%
            </Badge>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Simulação recomendada</CardTitle>
            </CardHeader>
            <CardContent>
              {visual.status === "completed" && visual.image_data_url ? (
                <Image
                  src={visual.image_data_url}
                  alt="Simulação visual do corte recomendado"
                  width={1024}
                  height={1024}
                  unoptimized
                  className="h-auto w-full rounded-lg object-cover"
                />
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                  A simulação visual ainda não foi concluída.
                  {userFacing.visual_error ? ` ${userFacing.visual_error}` : ""}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recomendação principal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {primary ? (
                <>
                  <div>
                    <h2 className="text-xl font-semibold">{primary.display_name}</h2>
                    {primary.why_it_works && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {primary.why_it_works}
                      </p>
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold">Instruções para o barbeiro</h3>
                    <p className="mt-1 text-sm leading-6">{primary.barber_instructions}</p>
                  </div>
                  {primary.styling && (
                    <div>
                      <h3 className="font-semibold">Finalização</h3>
                      <p className="mt-1 text-sm leading-6">{primary.styling}</p>
                    </div>
                  )}
                  {primary.hair_data_note && (
                    <p className="rounded-md bg-muted p-3 text-sm">{primary.hair_data_note}</p>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Nenhuma recomendação principal disponível.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {recommendations.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Opções recomendadas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {recommendations.map((item: any, index: number) => (
                  <div key={`${item.technical_id}-${index}`} className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Opção {index + 1}</p>
                    <h3 className="mt-1 font-semibold">{item.display_name}</h3>
                    <p className="mt-2 text-sm leading-6">{item.barber_instructions}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}
