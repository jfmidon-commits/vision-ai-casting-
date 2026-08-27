import {
  clearActiveAnalysis,
  getActiveAnalysis,
  getLastCompletedAnalysis,
  setActiveAnalysis,
  setLastCompletedAnalysis,
} from '../lib/visagism-storage';

describe('visagism analysis storage', () => {
  beforeEach(() => {
    window.localStorage.clear();
    jest.restoreAllMocks();
  });

  test('persists and recovers an active analysis', () => {
    setActiveAnalysis('analysis-active');

    expect(getActiveAnalysis()).toEqual(
      expect.objectContaining({ analysisId: 'analysis-active' })
    );
  });

  test('discard corrupt active-analysis storage without throwing', () => {
    window.localStorage.setItem('vision:visagism:active-analysis', '{invalid-json');

    expect(() => getActiveAnalysis()).not.toThrow();
    expect(getActiveAnalysis()).toBeNull();
    expect(window.localStorage.getItem('vision:visagism:active-analysis')).toBeNull();
  });

  test('expires stale active analyses after 24 hours', () => {
    const now = 2_000_000_000_000;
    jest.spyOn(Date, 'now').mockReturnValue(now);
    window.localStorage.setItem(
      'vision:visagism:active-analysis',
      JSON.stringify({ analysisId: 'stale', startedAt: now - 24 * 60 * 60 * 1000 - 1 })
    );

    expect(getActiveAnalysis()).toBeNull();
  });

  test('last completed analysis survives clearing active analysis', () => {
    setLastCompletedAnalysis({
      analysisId: 'analysis-completed',
      profileId: 'profile-1',
      faceShapeCategory: 'round',
      primaryHairstyle: 'Quiff texturizado',
      confidenceScore: 0.95,
    });
    setActiveAnalysis('analysis-next');

    clearActiveAnalysis();

    expect(getActiveAnalysis()).toBeNull();
    expect(getLastCompletedAnalysis()).toEqual(
      expect.objectContaining({
        analysisId: 'analysis-completed',
        profileId: 'profile-1',
        primaryHairstyle: 'Quiff texturizado',
      })
    );
  });

  test('rejects a completed-analysis entry that is not bound to a profile', () => {
    window.localStorage.setItem(
      'vision:visagism:last-completed-analysis',
      JSON.stringify({ analysisId: 'analysis-completed', completedAt: Date.now() })
    );

    expect(getLastCompletedAnalysis()).toBeNull();
    expect(
      window.localStorage.getItem('vision:visagism:last-completed-analysis')
    ).toBeNull();
  });
});
