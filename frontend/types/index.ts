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

export interface HaircutRecommendation {
  rank: number;
  key: string;
  name: string;
  compatibility_score: number;
  top_cm: number[];
  sides_mm: number[];
  fade: string;
  connection: string;
  direction: string;
  finish: string;
  maintenance: string;
  avoid: string;
  reasons: string[];
  risks: string[];
  evidence: Record<string, unknown>;
}

export interface FullVisagismAnalysis {
  schema_version: string;
  analysis_id?: string;
  photoshoot_id: string;
  status: string;
  processed_images: number;
  selected_views: Record<string, unknown>;
  face_shape?: Record<string, unknown>;
  measurements: Record<string, unknown>;
  hair_analysis: Record<string, unknown>;
  recommendations: HaircutRecommendation[];
  top_recommendation?: HaircutRecommendation;
  card_url?: string;
  manifest_url?: string;
  simulation_url?: string;
  analysis_sources: string[];
  limitations: string[];
  integrity: Record<string, unknown>;
}

export interface Analysis {
  id: string;
  status: string;
  confidence_score?: number;
  facial_structure?: unknown;
  visagism?: FullVisagismAnalysis;
  casting?: unknown;
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
