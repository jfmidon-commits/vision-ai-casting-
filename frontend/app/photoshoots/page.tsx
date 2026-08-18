"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Camera, Plus, Calendar, MapPin } from "lucide-react";

const photoshoots = [
  { id: "1", title: "Ensaio Editorial - João", type: "studio", date: "2026-08-05", location: "Estúdio Central", status: "completed", photo_count: 24 },
  { id: "2", title: "Ensaio Outdoor - Maria", type: "location", date: "2026-08-03", location: "Praia de Copacabana", status: "processing", photo_count: 18 },
  { id: "3", title: "Update Book - Pedro", type: "update", date: "2026-08-01", location: "Estúdio Central", status: "pending", photo_count: 0 },
];

export default function PhotoshootsPage() {
  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Ensaios Fotográficos</h1>
            <p className="text-muted-foreground">Gerencie sessões de fotos</p>
          </div>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Novo Ensaio
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {photoshoots.map((shoot) => (
            <Card key={shoot.id} className="hover:shadow-lg transition-shadow">
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
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    {new Date(shoot.date).toLocaleDateString("pt-BR")}
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    {shoot.location}
                  </div>
                  <div className="flex items-center gap-2">
                    <Camera className="h-4 w-4" />
                    {shoot.photo_count} fotos
                  </div>
                </div>
                <Button variant="outline" className="w-full mt-4" size="sm">
                  Ver Detalhes
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </DashboardShell>
  );
}
