"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateProfile, useProfiles } from "@/hooks/use-profiles";
import { Plus, Search, Filter, X } from "lucide-react";

export default function ProfilesPage() {
  const { data: profiles, isLoading } = useProfiles();
  const createProfile = useCreateProfile();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [showCreate, setShowCreate] = useState(false);
  const [fullName, setFullName] = useState("");
  const [artisticName, setArtisticName] = useState("");
  const [code, setCode] = useState("");
  const [formError, setFormError] = useState("");

  const filteredProfiles = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (profiles || []).filter((profile: any) => {
      const matchesSearch = !term || [profile.full_name, profile.artistic_name, profile.code]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term));
      const matchesStatus = statusFilter === "all" || profile.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [profiles, search, statusFilter]);

  const cycleFilter = () => {
    setStatusFilter((current) => current === "all" ? "active" : current === "active" ? "inactive" : "all");
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError("");
    if (fullName.trim().length < 2) {
      setFormError("Informe um nome com pelo menos 2 caracteres.");
      return;
    }
    try {
      await createProfile.mutateAsync({
        full_name: fullName.trim(),
        artistic_name: artisticName.trim() || undefined,
        code: code.trim() || undefined,
      });
      setFullName("");
      setArtisticName("");
      setCode("");
      setShowCreate(false);
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || "Não foi possível criar o perfil.");
    }
  };

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Perfis</h1>
            <p className="text-muted-foreground">Gerencie atores e modelos</p>
          </div>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Novo Perfil
          </Button>
        </div>

        {showCreate && (
          <Card className="border-primary/30">
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="font-semibold">Criar novo perfil</div>
              <Button variant="ghost" size="icon" onClick={() => setShowCreate(false)} aria-label="Fechar">
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-2 sm:col-span-2">
                  <Label htmlFor="full-name">Nome completo</Label>
                  <Input id="full-name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Nome do ator ou modelo" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="artistic-name">Nome artístico</Label>
                  <Input id="artistic-name" value={artisticName} onChange={(e) => setArtisticName(e.target.value)} placeholder="Opcional" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="code">Código</Label>
                  <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Opcional" />
                </div>
                {formError && <p className="text-sm text-destructive sm:col-span-2">{formError}</p>}
                <div className="flex gap-2 sm:col-span-2">
                  <Button type="submit" disabled={createProfile.isPending}>
                    {createProfile.isPending ? "Salvando..." : "Salvar Perfil"}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar perfis..."
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <Button variant="outline" size="sm" onClick={cycleFilter}>
                <Filter className="mr-2 h-4 w-4" />
                {statusFilter === "all" ? "Todos" : statusFilter === "active" ? "Ativos" : "Inativos"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="py-8 text-center text-muted-foreground">Carregando...</div>
            ) : filteredProfiles.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">Nenhum perfil encontrado.</div>
            ) : (
              <div className="space-y-4">
                {filteredProfiles.map((profile: any) => (
                  <div key={profile.id} className="flex flex-col gap-3 rounded-lg border p-4 hover:bg-accent/50 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                        {profile.full_name?.charAt(0) || "?"}
                      </div>
                      <div>
                        <p className="font-medium">{profile.full_name}</p>
                        <p className="text-sm text-muted-foreground">{profile.artistic_name || profile.code || "Sem código"}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={profile.status === "active" ? "default" : "secondary"}>
                        {profile.status === "active" ? "Ativo" : "Inativo"}
                      </Badge>
                      <Link href={`/profiles/${profile.id}`}>
                        <Button variant="outline" size="sm">Abrir</Button>
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
