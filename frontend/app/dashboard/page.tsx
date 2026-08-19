"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Users, Camera, Brain, FileText, TrendingUp, Activity } from "lucide-react";

const stats = [
  { name: "Total de Perfis", value: "124", icon: Users, change: "+12%", trend: "up" },
  { name: "Ensaios este mês", value: "38", icon: Camera, change: "+8%", trend: "up" },
  { name: "Análises de IA", value: "256", icon: Brain, change: "+24%", trend: "up" },
  { name: "Relatórios gerados", value: "89", icon: FileText, change: "+15%", trend: "up" },
];

const recentActivity = [
  { id: 1, action: "Análise completada", subject: "João Silva", time: "2 min atrás", type: "success" },
  { id: 2, action: "Novo perfil criado", subject: "Maria Santos", time: "15 min atrás", type: "info" },
  { id: 3, action: "Relatório PDF gerado", subject: "Pedro Costa", time: "1h atrás", type: "success" },
  { id: 4, action: "Ensaio finalizado", subject: "Ana Oliveira", time: "2h atrás", type: "info" },
];

export default function DashboardPage() {
  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">Visão geral da sua agência</p>
          </div>
          <Button>Novo Perfil</Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.name}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{stat.name}</CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-green-600">{stat.change}</span> vs mês anterior
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Atividade Recente</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentActivity.map((activity) => (
                  <div key={activity.id} className="flex items-center gap-4">
                    <div className={`h-2 w-2 rounded-full ${activity.type === "success" ? "bg-green-500" : "bg-blue-500"}`} />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{activity.action}</p>
                      <p className="text-xs text-muted-foreground">{activity.subject}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">{activity.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Uso do Plano</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Perfis</span>
                    <span className="font-medium">124 / 500</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-secondary">
                    <div className="h-2 rounded-full bg-primary" style={{ width: "25%" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Análises</span>
                    <span className="font-medium">256 / 1000</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-secondary">
                    <div className="h-2 rounded-full bg-primary" style={{ width: "26%" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Armazenamento</span>
                    <span className="font-medium">45GB / 100GB</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-secondary">
                    <div className="h-2 rounded-full bg-primary" style={{ width: "45%" }} />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}
