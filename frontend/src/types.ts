export type RiskLevel = 'LOW' | 'MED' | 'HIGH';

export interface Citation {
  source: string;
  page: number | null;
  section: string | null;
  quote: string | null;
}

export interface AskRequest {
  question: string;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  risk_level: RiskLevel;
  contexts: string[];
}

export interface ChatMessage {
  id: string;
  question: string;
  response: AskResponse | null;
  isLoading: boolean;
  error: string | null;
}

export interface Chat {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

// =============================================================================
// MAINTENANCE PLAN TYPES
// =============================================================================

export type Season = 'spring' | 'summer' | 'fall' | 'winter';

export type ClimateZone = 'cold' | 'mixed' | 'hot_humid' | 'hot_dry';

export type HouseType = 'single_family' | 'townhouse' | 'condo' | 'duplex';

export interface InstalledSystem {
  model: string | null;
  manufacturer: string | null;
  fuel_type: string | null;
  install_year: number | null;
  notes: string | null;
}

export interface HouseProfile {
  name: string;
  year_built: number | null;
  square_footage: number | null;
  climate_zone: ClimateZone;
  house_type: HouseType;
  systems: Record<string, InstalledSystem | null>;
}

export interface ChecklistItem {
  task: string;
  device_type: string | null;
  priority: string;
  frequency: string | null;
  estimated_time: string | null;
  notes: string | null;
  source_doc: string | null;
}

export interface MaintenancePlanRequest {
  season: Season;
  house_profile_path?: string | null;
}

export interface MaintenancePlanResponse {
  season: Season;
  house_name: string;
  checklist_items: ChecklistItem[];
  markdown: string;
  sources_used: string[];
}
