"use client";

import Link from "next/link";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, Camera, Brain, FileText } from "lucide-react";

const stats = [
  { name: "Total de Perfis", value: "124", icon: Users, change: "+12%" },
  { name: "Ensaios este mês", value: "38", icon: Camera, change: "+8%" },
  { name: "Análises de IA", value: "256", icon: Brain, change: "+24%" },
  { name: "Relatórios gerados", value: "89", icon: FileText, change: "+15%" },
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
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">Visão geral da sua agência</p>
          </div>
          <Link href="/profiles">
            <Button className="w-full sm:w-auto">Novo Perfil</Button>
          </Link>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
            <CardHeader><CardTitle>Atividade Recente</CardTitle></CardHeader>
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
            <CardHeader><CardTitle>Uso do Plano</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  ["Perfis", "124 / 500", "25%"],
                  ["Análises", "256 / 1000", "26%"],
                  ["Armazenamento", "45GB / 100GB", "45%"],
                ].map(([label, value, width]) => (
                  <div key={label}>
                    <div className="flex justify-between text-sm"><span>{label}</span><span className="font-medium">{value}</span></div>
                    <div className="mt-2 h-2 rounded-full bg-secondary"><div className="h-2 rounded-full bg-primary" style={{ width }} /></div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}
