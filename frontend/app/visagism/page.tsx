"use client";

import Image from "next/image";
import { FormEvent, useMemo, useState } from "react";
import { Scissors, Upload } from "lucide-react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { visagismApi } from "@/lib/api";

export default function VisagismPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await visagismApi.analyzeUpload(file, "front");
      setResult(response.data.data);
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          "Não foi possível concluir a análise."
      );
    } finally {
      setLoading(false);
    }
  };

  const userFacing = result?.user_facing_result || {};
  const primary = userFacing.primary_recommendation;
  const recommendations = userFacing.recommendations || [];
  const visual = userFacing.visual_simulation || {};

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Visagismo</h1>
          <p className="text-muted-foreground">
            Envie uma foto frontal para receber análise facial, corte recomendado e simulação visual.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Foto para análise
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
                className="block w-full rounded-md border p-3 text-sm"
              />

              {previewUrl && (
                <Image
                  src={previewUrl}
                  alt="Prévia da foto selecionada"
                  width={512}
                  height={512}
                  unoptimized
                  className="max-h-96 w-auto rounded-lg border object-contain"
                />
              )}

              <Button type="submit" disabled={!file || loading}>
                <Scissors className="mr-2 h-4 w-4" />
                {loading ? "Analisando e gerando simulação..." : "Analisar visagismo"}
              </Button>
            </form>

            {error && (
              <p className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </p>
            )}
          </CardContent>
        </Card>

        {result && (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant={userFacing.complete ? "default" : "secondary"}>
                {userFacing.complete ? "Resultado completo" : "Simulação visual pendente"}
              </Badge>
              {userFacing.face_shape && (
                <Badge variant="outline">Rosto: {userFacing.face_shape}</Badge>
              )}
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Simulação visual</CardTitle>
                </CardHeader>
                <CardContent>
                  {visual.status === "completed" && visual.image_data_url ? (
                    <Image
                      src={visual.image_data_url}
                      alt="Simulação do corte recomendado"
                      width={1024}
                      height={1024}
                      unoptimized
                      className="h-auto w-full rounded-lg object-cover"
                    />
                  ) : (
                    <div className="rounded-lg border border-dashed p-8 text-sm text-muted-foreground">
                      A parte textual foi calculada, mas a imagem ainda não foi concluída.
                      {userFacing.visual_error ? ` ${userFacing.visual_error}` : ""}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Melhor corte</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {primary ? (
                    <>
                      <h2 className="text-xl font-semibold">{primary.display_name}</h2>
                      {primary.why_it_works && (
                        <p className="text-sm leading-6 text-muted-foreground">
                          {primary.why_it_works}
                        </p>
                      )}
                      <div>
                        <h3 className="font-semibold">Para o barbeiro</h3>
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
                      Nenhuma recomendação principal foi produzida.
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            {recommendations.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>5 opções recomendadas</CardTitle>
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
          </>
        )}
      </div>
    </DashboardShell>
  );
}
