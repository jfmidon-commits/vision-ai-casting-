"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Download, Eye, FileDown } from "lucide-react";

const reports = [
  { id: "1", title: "Relatório Completo - João Silva", status: "published", confidence: 0.85, date: "2026-08-05" },
  { id: "2", title: "Relatório Completo - Maria Santos", status: "draft", confidence: 0.78, date: "2026-08-04" },
  { id: "3", title: "Relatório Completo - Pedro Costa", status: "published", confidence: 0.92, date: "2026-08-03" },
];

export default function ReportsPage() {
  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Relatórios</h1>
            <p className="text-muted-foreground">Visualize e exporte relatórios de análise</p>
          </div>
          <Button>
            <FileText className="mr-2 h-4 w-4" />
            Novo Relatório
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Relatórios Gerados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex items-center gap-4">
                    <FileText className="h-5 w-5 text-primary" />
                    <div>
                      <p className="font-medium">{report.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(report.date).toLocaleDateString("pt-BR")} • 
                        Confiança: {(report.confidence * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={report.status === "published" ? "default" : "secondary"}>
                      {report.status === "published" ? "Publicado" : "Rascunho"}
                    </Badge>
                    <Button variant="ghost" size="icon">
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
