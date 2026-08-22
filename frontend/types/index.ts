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
  displayMode?: "original" | "validated_hair_beard_overlay" | "original_plus_spec";
}

export interface SimulationPreflightResult {
  analysis_id: string;
  selected_haircut: string;
  simulation_status: "blocked";
  reason: string;
  provider_configured: false;
  ready_enabled: false;
  reference_count: number;
  card_media: VisagismCardMedia;
}

export interface Analysis {
  id: string;
  status: string;
  confidence_score?: number;
  facial_structure?: any;
  visagism?: any;
  casting?: any;
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
