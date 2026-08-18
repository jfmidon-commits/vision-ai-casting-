"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useProfiles } from "@/hooks/use-profiles";
import { Plus, Search, Filter, MoreHorizontal } from "lucide-react";
import Link from "next/link";

export default function ProfilesPage() {
  const { data: profiles, isLoading } = useProfiles();

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Perfis</h1>
            <p className="text-muted-foreground">Gerencie atores e modelos</p>
          </div>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Novo Perfil
          </Button>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Buscar perfis..."
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <Button variant="outline" size="sm">
                <Filter className="mr-2 h-4 w-4" />
                Filtros
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="py-8 text-center text-muted-foreground">Carregando...</div>
            ) : (
              <div className="space-y-4">
                {(profiles || []).map((profile: any) => (
                  <div
                    key={profile.id}
                    className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent/50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                        {profile.full_name?.charAt(0) || "?"}
                      </div>
                      <div>
                        <p className="font-medium">{profile.full_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {profile.artistic_name || profile.code || "Sem código"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge variant={profile.status === "active" ? "default" : "secondary"}>
                        {profile.status === "active" ? "Ativo" : "Inativo"}
                      </Badge>
                      <Link href={`/profiles/${profile.id}`}>
                        <Button variant="ghost" size="sm">
                          Ver
                        </Button>
                      </Link>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
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
