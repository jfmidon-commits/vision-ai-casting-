"use client";

import Link from "next/link";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAnalyses } from "@/hooks/use-analyses";
import { Brain, Clock, CheckCircle, AlertCircle } from "lucide-react";

export default function AnalysesPage() {
  const { data: analyses, isLoading } = useAnalyses();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "processing":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "failed":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="default">Concluída</Badge>;
      case "processing":
        return <Badge variant="secondary">Processando</Badge>;
      case "failed":
        return <Badge variant="destructive">Falhou</Badge>;
      default:
        return <Badge variant="outline">Pendente</Badge>;
    }
  };

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Análises de IA</h1>
            <p className="text-muted-foreground">Histórico de análises e resultados</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <Brain className="h-8 w-8 text-primary" />
                <div>
                  <p className="text-2xl font-bold">256</p>
                  <p className="text-sm text-muted-foreground">Total de análises</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <CheckCircle className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-2xl font-bold">98%</p>
                  <p className="text-sm text-muted-foreground">Taxa de sucesso</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <Clock className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="text-2xl font-bold">42s</p>
                  <p className="text-sm text-muted-foreground">Tempo médio</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Histórico de Análises</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="py-8 text-center text-muted-foreground">Carregando...</div>
            ) : (
              <div className="space-y-4">
                {(analyses || []).map((analysis: any) => (
                  <div
                    key={analysis.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div className="flex items-center gap-4">
                      {getStatusIcon(analysis.status)}
                      <div>
                        <p className="font-medium">Análise #{analysis.id.slice(0, 8)}</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(analysis.created_at).toLocaleDateString("pt-BR")}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {analysis.confidence_score && (
                        <span className="text-sm text-muted-foreground">
                          Confiança: {(analysis.confidence_score * 100).toFixed(0)}%
                        </span>
                      )}
                      {getStatusBadge(analysis.status)}
                      <Link
                        href={`/analyses/${analysis.id}`}
                        className="rounded-md px-3 py-2 text-sm font-medium hover:bg-accent"
                      >
                        Ver
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
