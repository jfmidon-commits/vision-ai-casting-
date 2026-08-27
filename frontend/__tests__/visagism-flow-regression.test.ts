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

test('409 polling failure clears stale analysis state', () => {
  const source = readFrontendFile('app/visagism/page.tsx');
  expect(source).toContain('getStatusCode(error) === 409');
  expect(source).toContain('clearPersistedAnalysis();');
  expect(source).toContain('setAnalysisId(null);');
});

test('auth and mobile upload requests have dedicated longer timeouts', () => {
  const source = readFrontendFile('lib/api.ts');
  expect(source).toContain('const AUTH_TIMEOUT_MS = 60000;');
  expect(source).toContain('const UPLOAD_TIMEOUT_MS = 120000;');
  expect(source).toContain('timeout: AUTH_TIMEOUT_MS');
  expect(source).toContain('timeout: UPLOAD_TIMEOUT_MS');
});
