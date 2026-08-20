"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCreatePhotoshoot } from "@/hooks/use-photoshoots";
import { useProfiles } from "@/hooks/use-profiles";

export default function NewPhotoshootPage() {
  const router = useRouter();
  const { data: profiles = [], isLoading: profilesLoading } = useProfiles();
  const createPhotoshoot = useCreatePhotoshoot();
  const [profileId, setProfileId] = useState("");
  const [title, setTitle] = useState("");
  const [type, setType] = useState("studio");
  const [date, setDate] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!profileId || !title.trim()) {
      setError("Selecione um perfil e informe o título do ensaio.");
      return;
    }
    try {
      const response = await createPhotoshoot.mutateAsync({
        profile_id: profileId,
        title: title.trim(),
        type,
        date: date || undefined,
        location: location.trim() || undefined,
      });
      const id = response.data?.data?.id as string | undefined;
      router.push(id ? `/photoshoots/${id}` : "/photoshoots");
    } catch {
      setError("Não foi possível criar o ensaio. Verifique os dados e tente novamente.");
    }
  };

  return (
    <DashboardShell>
      <div className="mx-auto w-full max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Novo Ensaio</h1>
          <p className="text-muted-foreground">Crie a sessão que receberá as fotos para o Visagismo.</p>
        </div>

        <Card>
          <CardHeader><CardTitle>Dados do ensaio</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <label className="block space-y-1 text-sm font-medium">
                <span>Perfil</span>
                <select
                  value={profileId}
                  onChange={(event) => setProfileId(event.target.value)}
                  disabled={profilesLoading}
                  className="h-10 w-full rounded-md border bg-background px-3"
                >
                  <option value="">Selecione um perfil</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.artistic_name || profile.full_name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-1 text-sm font-medium">
                <span>Título</span>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Ex.: Visagismo agosto 2026"
                  className="h-10 w-full rounded-md border bg-background px-3"
                />
              </label>

              <label className="block space-y-1 text-sm font-medium">
                <span>Tipo</span>
                <select value={type} onChange={(event) => setType(event.target.value)} className="h-10 w-full rounded-md border bg-background px-3">
                  <option value="studio">Estúdio</option>
                  <option value="location">Locação</option>
                  <option value="composite">Composite</option>
                  <option value="update">Atualização</option>
                </select>
              </label>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block space-y-1 text-sm font-medium">
                  <span>Data</span>
                  <input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="h-10 w-full rounded-md border bg-background px-3" />
                </label>
                <label className="block space-y-1 text-sm font-medium">
                  <span>Local</span>
                  <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Opcional" className="h-10 w-full rounded-md border bg-background px-3" />
                </label>
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                <Button type="button" variant="outline" onClick={() => router.push("/photoshoots")}>Cancelar</Button>
                <Button type="submit" disabled={createPhotoshoot.isPending || profilesLoading}>
                  {createPhotoshoot.isPending ? "Criando..." : "Criar ensaio"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
