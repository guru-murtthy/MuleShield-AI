export interface SHAPFeature {
  name: string;
  shap_value: number;
  direction: 'positive' | 'negative';
}

export interface DetectionPattern {
  pattern: string;
  confidence: number;
}

export interface ScoreResponse {
  account_id: string;
  risk_score: number;
  risk_band: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  ensemble_probability: number;
  component_probs: Record<string, number>;
  top_patterns: DetectionPattern[];
  shap_features: SHAPFeature[];
  narrative: string;
  auto_freeze_eligible: boolean;
  shap_available: boolean;
  str_draft?: Record<string, unknown>;
  model_version?: string;
  cached: boolean;
}

export interface AlertItem {
  account_id: string;
  risk_score: number;
  risk_band: string;
  top_pattern?: string;
  auto_freeze_eligible: boolean;
  scored_at?: string;
}

export interface AlertsResponse {
  items: AlertItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ActionResponse {
  account_id: string;
  action: string;
  status: string;
  reason?: string;
  applied_at?: string;
}

export interface HealthResponse {
  status: string;
  models_loaded: boolean;
  model_count: number;
  version: string;
}

export const RISK_BAND_COLORS: Record<string, string> = {
  MINIMAL: 'bg-gray-100 text-gray-700',
  LOW: 'bg-blue-100 text-blue-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-orange-100 text-orange-700',
  CRITICAL: 'bg-red-100 text-red-700',
};

export const RISK_BAND_DOT: Record<string, string> = {
  MINIMAL: 'bg-gray-400',
  LOW: 'bg-blue-500',
  MEDIUM: 'bg-yellow-500',
  HIGH: 'bg-orange-500',
  CRITICAL: 'bg-red-600',
};
