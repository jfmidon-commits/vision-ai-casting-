import fs from 'fs';
import path from 'path';

function readFrontendFile(relativePath: string) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

test('triage and analysis are separate user actions', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('Enviar fotos para triagem');
  expect(source).toContain('Iniciar análise');
  expect(source).toContain('setActivePhotoshootId(photoshootId)');
  expect(source).toContain('if (!activePhotoshootId || !allTriaged) return;');
});

test('triage status is committed per photo instead of only after the whole batch', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('setUploaded((current) => ({');
  expect(source).toContain('[photo.angle]: { photoId, triage }');
});

test('409 polling failure clears stale active analysis state', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('getStatusCode(error) === 409');
  expect(source).toContain('clearActiveAnalysis();');
  expect(source).toContain('setAnalysisId(null);');
});

test('completed visagism results become recoverable by URL and local storage', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('url.searchParams.set("analysisId", analysisId)');
  expect(source).toContain('getLastCompletedAnalysis()');
  expect(source).toContain('setLastCompletedAnalysis({');
  expect(source).toContain('recoverAnalysis(urlAnalysisId, "url")');
});

test('refresh recovery preserves the current analysis instead of starting a new one', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('const active = getActiveAnalysis();');
  expect(source).toContain('setAnalysisId(active.analysisId)');
  expect(source).toContain('setStep("processing")');
  expect(source).toContain('VISAGISM_POLL_RECOVERED');
});

test('starting or resetting a flow does not delete the last completed analysis', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).not.toContain('clearLastCompletedAnalysis');
  expect(source).toContain('replaceAnalysisIdInUrl(null);');
  expect(source).toContain('clearActiveAnalysis();');
});

test('history is profile-scoped, sorted newest first and enriched from saved visagism', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('analysisApi.list({ profile_id: selectedProfileId })');
  expect(source).toContain('new Date(b.created_at).getTime() - new Date(a.created_at).getTime()');
  expect(source).toContain('.slice(0, 5)');
  expect(source).toContain('analysisApi.getVisagism(analysis.id)');
});

test('last completed result is shown only for the selected profile', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('lastCompleted.profileId === selectedProfileId');
  expect(source).toContain('Ver última análise');
  expect(source).toContain('Análises anteriores');
});

test('auth and mobile upload requests have dedicated longer timeouts', () => {
  const source = readFrontendFile('lib/api.ts');
  expect(source).toContain('const AUTH_TIMEOUT_MS = 60000;');
  expect(source).toContain('const UPLOAD_TIMEOUT_MS = 120000;');
  expect(source).toContain('timeout: AUTH_TIMEOUT_MS');
  expect(source).toContain('timeout: UPLOAD_TIMEOUT_MS');
});
