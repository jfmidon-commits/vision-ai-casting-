const ACTIVE_ANALYSIS_KEY = "vision:visagism:active-analysis";
const LAST_COMPLETED_ANALYSIS_KEY = "vision:visagism:last-completed-analysis";
const ACTIVE_ANALYSIS_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export type PersistedActiveAnalysis = {
  analysisId: string;
  startedAt: number;
};

export type PersistedCompletedAnalysis = {
  analysisId: string;
  profileId: string;
  completedAt: number;
  faceShapeCategory?: string;
  primaryHairstyle?: string | null;
  confidenceScore?: number;
};

function safeParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function getActiveAnalysis(): PersistedActiveAnalysis | null {
  if (typeof window === "undefined") return null;

  const persisted = safeParse<PersistedActiveAnalysis>(
    window.localStorage.getItem(ACTIVE_ANALYSIS_KEY)
  );

  const isValid =
    persisted !== null &&
    typeof persisted.analysisId === "string" &&
    persisted.analysisId.length > 0 &&
    typeof persisted.startedAt === "number" &&
    Number.isFinite(persisted.startedAt) &&
    Date.now() - persisted.startedAt < ACTIVE_ANALYSIS_MAX_AGE_MS;

  if (!isValid) {
    clearActiveAnalysis();
    return null;
  }

  return persisted;
}

export function setActiveAnalysis(analysisId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    ACTIVE_ANALYSIS_KEY,
    JSON.stringify({ analysisId, startedAt: Date.now() } satisfies PersistedActiveAnalysis)
  );
}

export function clearActiveAnalysis(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_ANALYSIS_KEY);
}

export function getLastCompletedAnalysis(): PersistedCompletedAnalysis | null {
  if (typeof window === "undefined") return null;

  const persisted = safeParse<PersistedCompletedAnalysis>(
    window.localStorage.getItem(LAST_COMPLETED_ANALYSIS_KEY)
  );

  const isValid =
    persisted !== null &&
    typeof persisted.analysisId === "string" &&
    persisted.analysisId.length > 0 &&
    typeof persisted.profileId === "string" &&
    persisted.profileId.length > 0 &&
    typeof persisted.completedAt === "number" &&
    Number.isFinite(persisted.completedAt);

  if (!isValid) {
    clearLastCompletedAnalysis();
    return null;
  }

  return persisted;
}

export function setLastCompletedAnalysis(
  data: Omit<PersistedCompletedAnalysis, "completedAt"> & { completedAt?: number }
): PersistedCompletedAnalysis | null {
  if (typeof window === "undefined") return null;

  const persisted: PersistedCompletedAnalysis = {
    ...data,
    completedAt: data.completedAt ?? Date.now(),
  };
  window.localStorage.setItem(LAST_COMPLETED_ANALYSIS_KEY, JSON.stringify(persisted));
  return persisted;
}

export function clearLastCompletedAnalysis(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LAST_COMPLETED_ANALYSIS_KEY);
}
