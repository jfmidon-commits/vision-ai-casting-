export interface Profile {
  id: string;
  tenant_id: string;
  code?: string;
  full_name: string;
  artistic_name?: string;
  birth_date?: string;
  gender?: string;
  height_cm?: number;
  weight_kg?: number;
  eye_color?: string;
  hair_color?: string;
  skin_tone?: string;
  body_type?: string;
  bio?: string;
  instagram?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Photoshoot {
  id: string;
  tenant_id: string;
  profile_id: string;
  title: string;
  type: string;
  date?: string;
  location?: string;
  status: string;
  photo_count: number;
  created_at: string;
}

export interface Photo {
  id: string;
  url: string;
  thumbnail_url?: string;
  angle: string;
  format: string;
  analysis_status: string;
}

export interface PhotoUploadResult {
  id: string;
  url: string;
  thumbnail_url: string;
  upload_url: string;
  expires_at: string;
}

export type PhotoTriageCategory =
  | "frontal_close"
  | "frontal"
  | "three_quarter_left"
  | "three_quarter_right"
  | "profile_left"
  | "profile_right"
  | "smiling"
  | "hairline"
  | "posterior"
  | "half_body"
  | "unknown"
  | "rejected";

export interface PhotoTriageResult {
  accepted: boolean;
  category: PhotoTriageCategory;
  confidence: number;
  selected: boolean;
  rejection_reasons: string[];
}

export interface VisagismCardMedia {
  personPhoto: string;
  displayImage: string;
  realPhotoVerified: boolean;
  realPhotoRefs?: string[];
  simulationApplied: boolean;
  identityVerified: boolean;
  fallbackUsed?: boolean;
  displayMode?:
    | "original"
    | "validated_hair_overlay"
    | "validated_hair_beard_overlay"
    | "original_plus_spec";
}

export interface BarberBrief {
  recommendation_name: string | null;
  grounded_in: string[];
  top: string;
  sides: string;
  back: string;
  fringe: string;
  texture: string;
  finish: string;
  avoid: string;
  note: string;
}

export interface SimulationPreflightResult {
  analysis_id: string;
  selected_haircut: string;
  simulation_status: "ready" | "blocked" | "processing";
  reason: string | null;
  provider_configured: boolean;
  ready_enabled: boolean;
  reference_count: number;
  cached: boolean;
  barber_brief?: BarberBrief | null;
  card_media: VisagismCardMedia;
}

export interface VisagismPrimaryRecommendation {
  name: string;
  why_it_works: string;
  visual_effect: string;
  professional_positioning: string;
  maintenance_level: "baixo" | "médio" | "alto" | "não determinado" | string;
  barber_instruction: string;
}

export interface VisagismAlternativeRecommendation {
  name: string;
  why_it_works: string;
  best_use_case: string;
  maintenance_level: "baixo" | "médio" | "alto" | "não determinado" | string;
}

export interface VisagismInterpretation {
  status: "ready" | "partial_grounded" | "service_limited" | "insufficient_grounded_data";
  executive_summary: string;
  current_hair_assessment: {
    summary: string;
    strengths: string[];
    attention_points: string[];
  };
  primary_recommendation: VisagismPrimaryRecommendation | null;
  alternative_hairstyles: VisagismAlternativeRecommendation[];
  barber_brief: BarberBrief;
  professional_image: {
    actor_casting: string;
    commercial_model: string;
    corporate_institutional: string;
    lifestyle_advertising: string;
  };
  limitations: string[];
  confidence_note: string;
}

export interface VisagismResult {
  face_shape_category?: string;
  recommended_hairstyles?: string[];
  primary_hairstyle?: string | null;
  primary_justification?: string | null;
  current_hair?: Record<string, unknown>;
  measured_data_used?: Record<string, unknown>;
  limitations?: string[];
  interpretation?: VisagismInterpretation;
}

export interface Analysis {
  id: string;
  status: string;
  confidence_score?: number;
  facial_structure?: unknown;
  visagism?: VisagismResult;
  casting?: unknown;
  card_media?: VisagismCardMedia;
  created_at: string;
}

export interface Report {
  id: string;
  title: string;
  status: string;
  confidence_index?: number;
  pdf_url?: string;
  created_at: string;
}
