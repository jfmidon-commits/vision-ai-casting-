"use client";

import { ChangeEvent, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Camera, ChevronLeft, ImagePlus, Sparkles, Upload } from "lucide-react";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  usePhotoshoot,
  usePhotoshootPhotos,
  useUploadPhotos,
} from "@/hooks/use-photoshoots";
import { useStartVisagism } from "@/hooks/use-visagism";

const ANGLES = [
  ["front", "Frontal"],
  ["left_45", "3/4 esquerdo"],
  ["right_45", "3/4 direito"],
  ["left_profile", "Perfil esquerdo"],
  ["right_profile", "Perfil direito"],
  ["smiling", "Sorrindo"],
  ["half_body", "Meio corpo"],
  ["neutral", "Neutra / linha frontal"],
] as const;

export default function PhotoshootDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const photoshootId = params.id;
  const { data: photoshoot, isLoading: loadingPhotoshoot } = usePhotoshoot(photoshootId);
  const { data: photos = [], isLoading: loadingPhotos } = usePhotoshootPhotos(photoshootId);
  const upload = useUploadPhotos(photoshootId);
  const startVisagism = useStartVisagism();
  const [files, setFiles] = useState<File[]>([]);
  const [angle, setAngle] = useState("front");
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);

  const canAnalyze = photos.length >= 3 && !startVisagism.isPending;
  const previewNames = useMemo(() => files.map((file) => file.name), [files]);

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    setFiles(Array.from(event.target.files || []));
    setUploadSummary(null);
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    const result = await upload.mutateAsync({ files, angle });
    setUploadSummary(
      result.failed > 0
        ? `${result.uploaded} de ${result.total} fotos enviadas. ${result.failed} falharam; você pode selecionar novamente apenas as que faltaram.`
        : `${result.uploaded} foto(s) enviada(s) com sucesso.`
    );
    setFiles([]);
  };

  const handleAnalyze = async () => {
    const response = await startVisagism.mutateAsync({ photoshootId });
    const analysisId = response.data?.data?.analysis_id as string | undefined;
    if (analysisId) router.push(`/analyses/${analysisId}/visagism`);
  };

  return (
    <DashboardShell>
      <div className="mx-auto w-full max-w-5xl space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Button variant="ghost" size="sm" className="mb-2 px-0" onClick={() => router.push("/photoshoots")}>
              <ChevronLeft className="mr-1 h-4 w-4" /> Voltar aos ensaios
            </Button>
            <h1 className="text-2xl font-bold sm:text-3xl">{photoshoot?.title || "Ensaio"}</h1>
            <p className="text-sm text-muted-foreground">
              Envie as fotos do ensaio e depois execute a análise completa de Visagismo.
            </p>
          </div>
          {photoshoot?.status && <Badge>{photoshoot.status}</Badge>}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ImagePlus className="h-5 w-5" /> Adicionar fotos
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-dashed p-4">
              <label className="flex cursor-pointer flex-col items-center gap-2 text-center">
                <Upload className="h-7 w-7 text-primary" />
                <span className="font-medium">Selecionar fotos do celular</span>
                <span className="text-xs text-muted-foreground">Você pode selecionar várias fotos de uma vez.</span>
                <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={handleFiles} />
              </label>
            </div>

            <div className="space-y-2">
              <label htmlFor="photo-angle" className="text-sm font-medium">Categoria das fotos selecionadas</label>
              <select id="photo-angle" value={angle} onChange={(event) => setAngle(event.target.value)} className="h-10 w-full rounded-md border bg-background px-3 text-sm">
                {ANGLES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <p className="text-xs text-muted-foreground">
                Para melhores resultados, envie grupos por ângulo. O Vision ainda fará a triagem automática das imagens.
              </p>
            </div>

            {previewNames.length > 0 && (
              <div className="rounded-md bg-muted p-3 text-sm">
                <p className="font-medium">{previewNames.length} foto(s) selecionada(s)</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{previewNames.join(", ")}</p>
              </div>
            )}

            <Button className="w-full sm:w-auto" disabled={files.length === 0 || upload.isPending} onClick={handleUpload}>
              <Upload className="mr-2 h-4 w-4" />
              {upload.isPending ? "Enviando..." : `Enviar ${files.length || ""} foto(s)`}
            </Button>
            {uploadSummary && <p className="text-sm text-muted-foreground">{uploadSummary}</p>}
            {upload.isError && <p className="text-sm text-destructive">Não foi possível iniciar o envio das fotos.</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-lg"><Camera className="h-5 w-5" /> Fotos do ensaio</CardTitle>
              <Badge variant="secondary">{photos.length}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {(loadingPhotoshoot || loadingPhotos) && <p className="text-sm text-muted-foreground">Carregando...</p>}
            {!loadingPhotos && photos.length === 0 && <p className="text-sm text-muted-foreground">Nenhuma foto enviada ainda.</p>}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              {photos.map((photo) => (
                <div key={photo.id} className="overflow-hidden rounded-lg border bg-muted">
                  <img src={photo.thumbnail_url || photo.url} alt={`Foto ${photo.angle}`} className="aspect-[3/4] w-full object-cover" />
                  <div className="p-2 text-xs">
                    <p className="truncate font-medium">{photo.angle}</p>
                    <p className="text-muted-foreground">{photo.analysis_status || "pending"}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-primary/30">
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Sparkles className="h-5 w-5 text-primary" /> Analisar Visagismo</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              O Vision vai selecionar as melhores vistas, medir proporções faciais, analisar o cabelo e gerar cinco cortes ranqueados com um card para o barbeiro.
            </p>
            {photos.length > 0 && photos.length < 3 && (
              <p className="text-sm text-amber-600">Envie pelo menos 3 fotos para liberar a análise. Para maior qualidade, use vistas diferentes.</p>
            )}
            {photos.length >= 3 && photos.length < 5 && (
              <p className="text-sm text-amber-600">A análise já pode ser executada, mas mais vistas podem reduzir limitações.</p>
            )}
            <Button className="w-full sm:w-auto" disabled={!canAnalyze} onClick={handleAnalyze}>
              <Sparkles className="mr-2 h-4 w-4" />
              {startVisagism.isPending ? "Iniciando análise..." : "Analisar Visagismo"}
            </Button>
            {startVisagism.isError && <p className="text-sm text-destructive">Não foi possível iniciar a análise.</p>}
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
