"use client";

import { useEffect, useState } from "react";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { photoshootApi } from "@/lib/api";
import { useProfiles } from "@/hooks/use-profiles";
import { Camera, Plus, Calendar, MapPin, X } from "lucide-react";

export default function PhotoshootsPage() {
  const { data: profiles } = useProfiles();
  const [photoshoots, setPhotoshoots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);
  const [profileId, setProfileId] = useState("");
  const [title, setTitle] = useState("");
  const [type, setType] = useState("studio");
  const [date, setDate] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const loadPhotoshoots = async () => {
    setLoading(true);
    try {
      const res = await photoshootApi.list();
      setPhotoshoots(res.data.data || []);
    } catch {
      setPhotoshoots([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadPhotoshoots(); }, []);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!profileId || !title.trim()) {
      setError("Selecione um perfil e informe o título do ensaio.");
      return;
    }
    setSaving(true);
    try {
      await photoshootApi.create({
        profile_id: profileId,
        title: title.trim(),
        type,
        date: date || undefined,
        location: location.trim() || undefined,
      });
      setShowCreate(false);
      setProfileId("");
      setTitle("");
      setDate("");
      setLocation("");
      await loadPhotoshoots();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Não foi possível criar o ensaio.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Ensaios Fotográficos</h1>
            <p className="text-muted-foreground">Gerencie sessões de fotos</p>
          </div>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Novo Ensaio
          </Button>
        </div>

        {showCreate && (
          <Card className="border-primary/30">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Novo Ensaio</CardTitle>
              <Button variant="ghost" size="icon" onClick={() => setShowCreate(false)}><X className="h-4 w-4" /></Button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-2 sm:col-span-2">
                  <Label>Perfil</Label>
                  <select value={profileId} onChange={(e) => setProfileId(e.target.value)} className="h-10 rounded-md border bg-background px-3 text-sm">
                    <option value="">Selecione um perfil</option>
                    {(profiles || []).map((profile: any) => <option key={profile.id} value={profile.id}>{profile.full_name}</option>)}
                  </select>
                </div>
                <div className="grid gap-2 sm:col-span-2"><Label>Título</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex.: Book comercial" /></div>
                <div className="grid gap-2"><Label>Tipo</Label><select value={type} onChange={(e) => setType(e.target.value)} className="h-10 rounded-md border bg-background px-3 text-sm"><option value="studio">Estúdio</option><option value="location">Locação</option><option value="composite">Composite</option><option value="update">Atualização</option></select></div>
                <div className="grid gap-2"><Label>Data</Label><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
                <div className="grid gap-2 sm:col-span-2"><Label>Local</Label><Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Opcional" /></div>
                {error && <p className="text-sm text-destructive sm:col-span-2">{error}</p>}
                <div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={saving}>{saving ? "Salvando..." : "Salvar Ensaio"}</Button><Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button></div>
              </form>
            </CardContent>
          </Card>
        )}

        {selected && (
          <Card className="border-primary/20">
            <CardHeader className="flex flex-row items-center justify-between"><CardTitle>{selected.title}</CardTitle><Button variant="ghost" size="icon" onClick={() => setSelected(null)}><X className="h-4 w-4" /></Button></CardHeader>
            <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
              <p><strong>Status:</strong> {selected.status || "pending"}</p>
              <p><strong>Fotos:</strong> {selected.photo_count || 0}</p>
              <p><strong>Local:</strong> {selected.location || "Não informado"}</p>
              <p><strong>Data:</strong> {selected.date ? new Date(selected.date).toLocaleDateString("pt-BR") : "Não informada"}</p>
            </CardContent>
          </Card>
        )}

        {loading ? <div className="py-8 text-center text-muted-foreground">Carregando...</div> : photoshoots.length === 0 ? <div className="py-8 text-center text-muted-foreground">Nenhum ensaio cadastrado.</div> : (
          <div className="grid gap-4 md:grid-cols-3">
            {photoshoots.map((shoot) => (
              <Card key={shoot.id} className="transition-shadow hover:shadow-lg">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <Camera className="h-5 w-5 text-primary" />
                    <Badge variant={shoot.status === "completed" ? "default" : shoot.status === "processing" ? "secondary" : "outline"}>{shoot.status === "completed" ? "Concluído" : shoot.status === "processing" ? "Processando" : "Pendente"}</Badge>
                  </div>
                  <CardTitle className="text-lg">{shoot.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2"><Calendar className="h-4 w-4" />{shoot.date ? new Date(shoot.date).toLocaleDateString("pt-BR") : "Sem data"}</div>
                    <div className="flex items-center gap-2"><MapPin className="h-4 w-4" />{shoot.location || "Sem local"}</div>
                    <div className="flex items-center gap-2"><Camera className="h-4 w-4" />{shoot.photo_count || 0} fotos</div>
                  </div>
                  <Button variant="outline" className="mt-4 w-full" size="sm" onClick={() => setSelected(shoot)}>Ver Detalhes</Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
