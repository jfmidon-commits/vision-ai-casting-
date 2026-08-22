import {
  buildVisagismCardExportMedia,
  resolveVisagismCardMedia,
  VisagismCardMediaError,
} from '../lib/visagism-card-media';

const realMedia = {
  personPhoto: '/photos/person-front.jpg',
  displayImage: '/photos/person-front.jpg',
  realPhotoVerified: true,
  realPhotoRefs: ['/photos/person-front.jpg', '/photos/person-side.jpg'],
  simulationApplied: false,
  identityVerified: false,
  displayMode: 'original' as const,
};

test('requires a verified real-person photo', () => {
  expect(() => resolveVisagismCardMedia({})).toThrow(VisagismCardMediaError);
});

test('personPhoto must be one of the actual analysis inputs', () => {
  expect(() =>
    resolveVisagismCardMedia({
      ...realMedia,
      personPhoto: '/generated/other-person.jpg',
    }),
  ).toThrow('person_photo_must_come_from_analysis_inputs');
});

test('unverified simulation falls back to the real photo', () => {
  const resolved = resolveVisagismCardMedia({
    ...realMedia,
    displayImage: '/generated/similar-face.jpg',
    simulationApplied: true,
    identityVerified: false,
  });

  expect(resolved.displayImage).toBe('/photos/person-front.jpg');
  expect(resolved.simulationApplied).toBe(false);
  expect(resolved.displayMode).toBe('original');
});

test('only an identity-verified hair/beard overlay may be displayed', () => {
  const resolved = resolveVisagismCardMedia({
    ...realMedia,
    displayImage: '/generated/validated-overlay.jpg',
    simulationApplied: true,
    identityVerified: true,
    displayMode: 'validated_hair_beard_overlay',
  });

  expect(resolved.personPhoto).toBe('/photos/person-front.jpg');
  expect(resolved.displayImage).toBe('/generated/validated-overlay.jpg');
  expect(resolved.simulationApplied).toBe(true);
});

test('export always preserves the original photo as identity anchor', () => {
  const exported = buildVisagismCardExportMedia({
    ...realMedia,
    displayImage: '/generated/validated-overlay.jpg',
    simulationApplied: true,
    identityVerified: true,
    displayMode: 'validated_hair_beard_overlay',
  });

  expect(exported.identityAnchorImage).toBe('/photos/person-front.jpg');
  expect(exported.originalPhoto).toBe('/photos/person-front.jpg');
  expect(exported.heroImage).toBe('/generated/validated-overlay.jpg');
  expect(exported.provenance).toBe('analysis_input_real_photo');
});
