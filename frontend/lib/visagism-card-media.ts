export type VisagismCardMedia = {
  personPhoto: string;
  displayImage: string;
  realPhotoVerified: boolean;
  realPhotoRefs: string[];
  simulationApplied: boolean;
  identityVerified: boolean;
  fallbackUsed?: boolean;
  displayMode?: 'original' | 'validated_hair_beard_overlay';
};

export class VisagismCardMediaError extends Error {}

/**
 * Final frontend gate for every visagism card/export/share surface.
 *
 * Golden rule: the card MUST be anchored to a verified real photo that came
 * from the person's own analysis inputs. A generated/similar portrait can
 * never become personPhoto. A simulation may only become displayImage when
 * backend identity validation already approved it; otherwise the real photo
 * is shown unchanged.
 */
export function resolveVisagismCardMedia(input: unknown): VisagismCardMedia {
  if (!input || typeof input !== 'object') {
    throw new VisagismCardMediaError('card_media_missing');
  }

  const media = input as Partial<VisagismCardMedia>;
  const personPhoto = typeof media.personPhoto === 'string' ? media.personPhoto.trim() : '';
  const refs = Array.isArray(media.realPhotoRefs)
    ? media.realPhotoRefs.filter((ref): ref is string => typeof ref === 'string' && ref.trim().length > 0)
    : [];

  if (!personPhoto || media.realPhotoVerified !== true) {
    throw new VisagismCardMediaError('verified_real_person_photo_required');
  }

  if (!refs.includes(personPhoto)) {
    throw new VisagismCardMediaError('person_photo_must_come_from_analysis_inputs');
  }

  const simulationApproved =
    media.simulationApplied === true &&
    media.identityVerified === true &&
    media.displayMode === 'validated_hair_beard_overlay' &&
    typeof media.displayImage === 'string' &&
    media.displayImage.trim().length > 0;

  if (!simulationApproved) {
    return {
      personPhoto,
      displayImage: personPhoto,
      realPhotoVerified: true,
      realPhotoRefs: refs,
      simulationApplied: false,
      identityVerified: false,
      fallbackUsed: true,
      displayMode: 'original',
    };
  }

  return {
    personPhoto,
    displayImage: media.displayImage as string,
    realPhotoVerified: true,
    realPhotoRefs: refs,
    simulationApplied: true,
    identityVerified: true,
    fallbackUsed: false,
    displayMode: 'validated_hair_beard_overlay',
  };
}

/**
 * Exports/share/PDF should always carry BOTH the immutable real photo and the
 * effective display image. This preserves provenance even when a validated
 * hair/beard overlay is shown.
 */
export function buildVisagismCardExportMedia(input: unknown) {
  const media = resolveVisagismCardMedia(input);
  return {
    identityAnchorImage: media.personPhoto,
    heroImage: media.displayImage,
    originalPhoto: media.personPhoto,
    realPhotoRefs: media.realPhotoRefs,
    simulationApplied: media.simulationApplied,
    identityVerified: media.identityVerified,
    provenance: 'analysis_input_real_photo' as const,
  };
}
