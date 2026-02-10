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

// =============================================================================
// TROUBLESHOOTING TYPES
// =============================================================================

export type QuestionType = 'yes_no' | 'multiple_choice' | 'free_text';

export type TroubleshootPhase = 'intake' | 'followup' | 'diagnosis' | 'safety_stop' | 'complete';

export interface FollowupQuestion {
  id: string;
  question: string;
  question_type: QuestionType;
  options: string[] | null;
  why: string;
}

export interface FollowupAnswer {
  question_id: string;
  answer: string;
}

export interface DiagnosticStep {
  step_number: number;
  instruction: string;
  expected_outcome: string;
  if_not_resolved: string;
  risk_level: RiskLevel;
  source_doc: string | null;
  requires_professional: boolean;
}

export interface TroubleshootStartRequest {
  device_type: string;
  symptom: string;
  urgency?: string;
  additional_context?: string | null;
}

export interface TroubleshootStartResponse {
  session_id: string;
  phase: TroubleshootPhase;
  risk_level: RiskLevel;
  followup_questions: FollowupQuestion[];
  preliminary_assessment: string | null;
  is_safety_stop: boolean;
  safety_message: string | null;
  recommended_professional: string | null;
}

export interface TroubleshootDiagnoseRequest {
  session_id: string;
  answers: FollowupAnswer[];
}

export interface TroubleshootDiagnoseResponse {
  session_id: string;
  diagnosis_summary: string;
  diagnostic_steps: DiagnosticStep[];
  overall_risk_level: RiskLevel;
  when_to_call_professional: string;
  markdown: string;
  sources_used: string[];
}

// =============================================================================
// PARTS HELPER TYPES
// =============================================================================

export type ConfidenceLevel = 'confirmed' | 'likely' | 'uncertain';

export interface PartRecommendation {
  part_name: string;
  part_number: string | null;
  device_type: string;
  device_model: string | null;
  description: string;
  replacement_interval: string | null;
  where_to_buy: string | null;
  confidence: ConfidenceLevel;
  source_doc: string | null;
  notes: string | null;
}

export interface ClarificationQuestion {
  id: string;
  question: string;
  reason: string;
  related_device: string | null;
}

export interface PartsLookupRequest {
  query: string;
  device_type?: string | null;
}

export interface PartsLookupResponse {
  parts: PartRecommendation[];
  clarification_questions: ClarificationQuestion[];
  summary: string;
  markdown: string;
  sources_used: string[];
  has_gaps: boolean;
}
