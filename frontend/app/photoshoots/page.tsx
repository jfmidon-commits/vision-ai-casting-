"use client";

import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Camera, Plus, Calendar, MapPin, Sparkles } from "lucide-react";
import { usePhotoshoots } from "@/hooks/use-photoshoots";
import { useStartVisagism } from "@/hooks/use-visagism";

export default function PhotoshootsPage() {
  const router = useRouter();
  const { data: photoshoots = [], isLoading, isError } = usePhotoshoots();
  const startVisagism = useStartVisagism();

  const handleVisagism = async (photoshootId: string) => {
    const response = await startVisagism.mutateAsync({ photoshootId });
    const analysisId = response.data?.data?.analysis_id as string | undefined;
    if (analysisId) {
      router.push(`/analyses/${analysisId}/visagism`);
    }
  };

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Ensaios Fotográficos</h1>
            <p className="text-muted-foreground">Gerencie sessões e execute o Visagismo real</p>
          </div>
          <Button onClick={() => router.push("/photoshoots/new")}>
            <Plus className="mr-2 h-4 w-4" />
            Novo Ensaio
          </Button>
        </div>

        {isLoading && <p className="text-sm text-muted-foreground">Carregando ensaios...</p>}
        {isError && <p className="text-sm text-destructive">Não foi possível carregar os ensaios.</p>}
        {!isLoading && !isError && photoshoots.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Nenhum ensaio encontrado. Crie um ensaio para começar.
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {photoshoots.map((shoot) => (
            <Card key={shoot.id} className="transition-shadow hover:shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Camera className="h-5 w-5 text-primary" />
                  <Badge variant={shoot.status === "completed" ? "default" : shoot.status === "processing" ? "secondary" : "outline"}>
                    {shoot.status === "completed" ? "Concluído" : shoot.status === "processing" ? "Processando" : "Pendente"}
                  </Badge>
                </div>
                <CardTitle className="text-lg">{shoot.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-muted-foreground">
                  {shoot.date && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      {new Date(shoot.date).toLocaleDateString("pt-BR")}
                    </div>
                  )}
                  {shoot.location && (
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4" />
                      {shoot.location}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Camera className="h-4 w-4" />
                    {shoot.photo_count} fotos
                  </div>
                </div>
                <div className="mt-4 grid gap-2">
                  <Button variant="outline" size="sm" onClick={() => router.push(`/photoshoots/${shoot.id}`)}>
                    Ver Detalhes
                  </Button>
                  <Button
                    size="sm"
                    disabled={shoot.photo_count < 1 || startVisagism.isPending}
                    onClick={() => handleVisagism(shoot.id)}
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    {startVisagism.isPending ? "Iniciando..." : "Analisar Visagismo"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </DashboardShell>
  );
}
