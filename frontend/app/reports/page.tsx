"use client";

import { useEffect, useMemo, useState } from "react";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { reportApi, photoshootApi } from "@/lib/api";
import { useProfiles } from "@/hooks/use-profiles";
import { FileText, Download, Eye, X } from "lucide-react";

export default function ReportsPage() {
  const { data: profiles } = useProfiles();
  const [reports, setReports] = useState<any[]>([]);
  const [photoshoots, setPhotoshoots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);
  const [profileId, setProfileId] = useState("");
  const [photoshootId, setPhotoshootId] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [reportsRes, shootsRes] = await Promise.all([reportApi.list(), photoshootApi.list()]);
      setReports(reportsRes.data.data || []);
      setPhotoshoots(shootsRes.data.data || []);
    } catch {
      setReports([]);
      setPhotoshoots([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadData(); }, []);

  const availableShoots = useMemo(() => photoshoots.filter((shoot) => !profileId || shoot.profile_id === profileId), [photoshoots, profileId]);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!profileId || !photoshootId || !title.trim()) {
      setError("Selecione perfil e ensaio e informe um título.");
      return;
    }
    setSaving(true);
    try {
      await reportApi.create({ profile_id: profileId, photoshoot_id: photoshootId, title: title.trim(), language: "pt-BR", template: "premium" });
      setShowCreate(false);
      setProfileId("");
      setPhotoshootId("");
      setTitle("");
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Não foi possível criar o relatório.");
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async (report: any) => {
    setDownloadingId(report.id);
    setError("");
    try {
      let url = report.pdf_url;
      if (!url) {
        const res = await reportApi.generatePdf(report.id);
        url = res.data?.data?.pdf_url;
      }
      if (url) window.open(url, "_blank", "noopener,noreferrer");
      else setError("O PDF ainda não está disponível.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Não foi possível gerar o PDF.");
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Relatórios</h1>
            <p className="text-muted-foreground">Visualize e exporte relatórios de análise</p>
          </div>
          <Button onClick={() => setShowCreate(true)}><FileText className="mr-2 h-4 w-4" />Novo Relatório</Button>
        </div>

        {showCreate && (
          <Card className="border-primary/30">
            <CardHeader className="flex flex-row items-center justify-between"><CardTitle>Novo Relatório</CardTitle><Button variant="ghost" size="icon" onClick={() => setShowCreate(false)}><X className="h-4 w-4" /></Button></CardHeader>
            <CardContent>
              <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-2"><Label>Perfil</Label><select value={profileId} onChange={(e) => { setProfileId(e.target.value); setPhotoshootId(""); }} className="h-10 rounded-md border bg-background px-3 text-sm"><option value="">Selecione</option>{(profiles || []).map((p: any) => <option key={p.id} value={p.id}>{p.full_name}</option>)}</select></div>
                <div className="grid gap-2"><Label>Ensaio</Label><select value={photoshootId} onChange={(e) => setPhotoshootId(e.target.value)} className="h-10 rounded-md border bg-background px-3 text-sm"><option value="">Selecione</option>{availableShoots.map((s: any) => <option key={s.id} value={s.id}>{s.title}</option>)}</select></div>
                <div className="grid gap-2 sm:col-span-2"><Label>Título</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex.: Relatório completo" /></div>
                {error && <p className="text-sm text-destructive sm:col-span-2">{error}</p>}
                <div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={saving}>{saving ? "Salvando..." : "Criar Relatório"}</Button><Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button></div>
              </form>
            </CardContent>
          </Card>
        )}

        {selected && (
          <Card className="border-primary/20">
            <CardHeader className="flex flex-row items-center justify-between"><CardTitle>{selected.title}</CardTitle><Button variant="ghost" size="icon" onClick={() => setSelected(null)}><X className="h-4 w-4" /></Button></CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p><strong>Status:</strong> {selected.status}</p>
              <p><strong>Versão:</strong> {selected.version || 1}</p>
              <p><strong>Confiança:</strong> {selected.confidence_index != null ? `${Math.round(selected.confidence_index * 100)}%` : "Não calculada"}</p>
              <p><strong>Criado em:</strong> {selected.created_at ? new Date(selected.created_at).toLocaleString("pt-BR") : "-"}</p>
            </CardContent>
          </Card>
        )}

        {error && !showCreate && <p className="text-sm text-destructive">{error}</p>}

        <Card>
          <CardHeader><CardTitle>Relatórios Gerados</CardTitle></CardHeader>
          <CardContent>
            {loading ? <div className="py-8 text-center text-muted-foreground">Carregando...</div> : reports.length === 0 ? <div className="py-8 text-center text-muted-foreground">Nenhum relatório cadastrado.</div> : (
              <div className="space-y-4">
                {reports.map((report) => (
                  <div key={report.id} className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                      <FileText className="h-5 w-5 text-primary" />
                      <div><p className="font-medium">{report.title}</p><p className="text-sm text-muted-foreground">{report.created_at ? new Date(report.created_at).toLocaleDateString("pt-BR") : "Sem data"}</p></div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={report.status === "published" ? "default" : "secondary"}>{report.status === "published" ? "Publicado" : "Rascunho"}</Badge>
                      <Button variant="outline" size="icon" onClick={() => setSelected(report)} aria-label="Visualizar"><Eye className="h-4 w-4" /></Button>
                      <Button variant="outline" size="icon" onClick={() => void handleDownload(report)} disabled={downloadingId === report.id} aria-label="Baixar PDF"><Download className="h-4 w-4" /></Button>
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
