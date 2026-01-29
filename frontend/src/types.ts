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
