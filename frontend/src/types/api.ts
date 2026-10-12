export interface MeetingRecord {
  id?: string;
  timestamp?: string;
  text: string;
}

export interface DecisionCandidate {
  text: string;
  topic: string;
  status: string;
  confidence: number;
  reversal: boolean;
  related_to?: string | null;
  evidence: string[];
}

export interface ReversalEvent {
  topic: string;
  previous: string;
  current: string;
  similarity: number;
  previous_status: string;
  current_status: string;
}

export interface AnalysisResponse {
  summary: string;
  candidates: DecisionCandidate[];
  reversed_decisions: ReversalEvent[];
  total_records: number;
  total_candidates: number;
  generated_at: string;
}
