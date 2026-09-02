"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { analysisApi, photoshootApi, profileApi, reportApi } from "@/lib/api";
import { Users, Camera, Brain, FileText } from "lucide-react";

type CollectionResponse = { data?: unknown[]; total?: number };
type DashboardData = {
  profiles: CollectionResponse;
  photoshoots: CollectionResponse;
  analyses: CollectionResponse;
  reports: CollectionResponse;
};

const emptyData: DashboardData = {
  profiles: {},
  photoshoots: {},
  analyses: {},
  reports: {},
};
const count = (collection: CollectionResponse) =>
  collection.total ?? collection.data?.length ?? 0;

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadDashboard() {
      setLoading(true);
      setError("");
      try {
        const params = { page: 1, per_page: 5 };
        const [profiles, photoshoots, analyses, reports] = await Promise.all([
          profileApi.list(params),
          photoshootApi.list(params),
          analysisApi.list(params),
          reportApi.list(params),
        ]);
        if (!active) return;
        setDashboard({
          profiles: profiles.data,
          photoshoots: photoshoots.data,
          analyses: analyses.data,
          reports: reports.data,
        });
      } catch {
        if (active) setError("Não foi possível carregar o resumo agora.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadDashboard();
    return () => {
      active = false;
    };
  }, []);

  const stats = useMemo(
    () => [
      { name: "Total de Perfis", value: count(dashboard.profiles), icon: Users },
      { name: "Ensaios", value: count(dashboard.photoshoots), icon: Camera },
      { name: "Análises de IA", value: count(dashboard.analyses), icon: Brain },
      { name: "Relatórios", value: count(dashboard.reports), icon: FileText },
    ],
    [dashboard]
  );

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">Dados reais da sua agência</p>
          </div>
          <Link href="/profiles">
            <Button className="w-full sm:w-auto">Novo Perfil</Button>
          </Link>
        </div>

        {error ? (
          <p className="rounded-md border border-destructive/30 p-3 text-sm text-destructive">
            {error}
          </p>
        ) : null}

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
                  <div className="text-2xl font-bold">
                    {loading ? "—" : stat.value}
                  </div>
                  <p className="text-xs text-muted-foreground">visível para o seu tenant</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Atalhos</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Button asChild variant="outline">
              <Link href="/profiles">Gerenciar perfis</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/photoshoots">Gerenciar ensaios</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/visagism">Nova análise</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/reports">Ver relatórios</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
