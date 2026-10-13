// Typed client for the ClaimPilot API.

export type Health = {
  ok: boolean;
  version: string;
  mode: "live" | "offline";
  backend: string;
  model: string | null;
  adjudicator_model: string | null;
  gemma_model: string | null;
  storage: { documents: string; files: string };
  seeded_on: string | null;
};

export type Policy = {
  policy_number: string;
  holder_name: string;
  first_name: string;
  phone_masked: string;
  language: string;
  language_name: string;
  vehicle: { registration: string; make_model: string; year: number; colour: string; segment: string };
  start_date: string;
  end_date: string;
  idv: number;
  addons: string[];
};

export type SampleKit = {
  key: "genuine" | "partial" | "fraud";
  title: string;
  blurb: string;
  policy_number: string;
  holder_name: string;
  first_name: string;
  language: string;
  language_name: string;
  vehicle: string;
  registration: string;
  statement: string;
  files: { name: string; kind: "photo" | "document"; mime: string }[];
  uses_real_photos: boolean;
};

export type TraceStep = {
  id: string;
  label: string;
  customer_label: string;
  engine: string;
  status: "pending" | "running" | "done" | "error";
  started_at?: string | null;
  ended_at?: string | null;
  ms?: number | null;
  summary: string;
};

export type ClaimFile = {
  id: string;
  name: string;
  kind: "photo" | "document" | "voice";
  mime: string;
  index?: number;
  url: string;
};

export type DamagedPart = {
  part_code: string;
  part_name: string;
  file_index: number;
  box_2d: number[];
  severity: "minor" | "moderate" | "severe";
  action: "repair" | "replace";
  confidence: number;
  observation: string;
};

export type Signal = {
  code: string;
  title: string;
  status: "pass" | "flag" | "info";
  severity: "none" | "low" | "medium" | "high";
  weight: number;
  evidence: string;
  data: Record<string, any>;
};

export type EstimateLine = {
  part_code: string;
  part_name: string;
  action: string;
  severity: string;
  material: string;
  parts_cost: number;
  labour_cost: number;
  paint_cost: number;
  gross: number;
  depreciation_pct: number;
  depreciation_amount: number;
  payable: number;
  excluded: boolean;
  note: string;
};

export type Recommendation = "approve" | "approve_partial" | "investigate" | "request_info" | "reject";

export type AI = {
  privacy: { masked_text: string; findings: { type: string; masked_as: string; by: string }[]; gemma_status: string; gemma_model: string | null };
  intake: {
    language: string;
    language_code: string;
    statement_english: string;
    incident_date: string;
    incident_time: string;
    incident_location: string;
    incident_type: string;
    incident_summary: string;
    vehicle_registration: string;
    vehicle_make_model: string;
    third_party_involved: boolean;
    injuries_reported: boolean;
    police_report_mentioned: boolean;
    documents: { file_index: number; file_name: string; doc_type: string; summary: string }[];
    bills: {
      file_index: number;
      vendor: string;
      bill_number: string;
      bill_date: string;
      kind: string;
      for_vehicle: boolean;
      line_items: { description: string; amount: number }[];
      subtotal: number;
      tax: number;
      total: number;
    }[];
    claimed_amount_inr: number;
    non_vehicle_items_claimed: string[];
    missing_information: string[];
  };
  coverage: {
    policy_active_on_incident_date: boolean;
    verdict: string;
    items: { item: string; status: "covered" | "excluded" | "limited"; reason: string; clause_ref: string; clause_quote: string }[];
    depreciation_applies: boolean;
    compulsory_deductible_inr: number;
    conditions_to_verify: string[];
    summary: string;
  };
  damage: {
    photos: { file_index: number; view: string; quality: string; notes: string }[];
    damaged_parts: DamagedPart[];
    impact_direction: string;
    consistent_with_statement: boolean;
    consistency_notes: string;
    possible_pre_existing_damage: string[];
    summary: string;
  };
  fraud_signals: { signals: Signal[]; rule_score: number; flags: number; checked: number };
  fraud: {
    risk_score: number;
    risk_level: "low" | "medium" | "high";
    red_flags: { title: string; severity: "low" | "medium" | "high"; evidence: string; source: string }[];
    document_tampering_suspected: boolean;
    recommended_checks: string[];
    summary: string;
  };
  estimate: {
    lines: EstimateLine[];
    gross_total: number;
    depreciation_total: number;
    excluded_total: number;
    deductible: number;
    assessed_payable: number;
    claimed_amount: number;
    vehicle_claimed_amount: number;
    bill_vs_estimate_variance_pct: number | null;
    recommended_payout: number;
    capped_by_bill: boolean;
    zero_dep: boolean;
    vehicle_age_months: number;
    segment: string;
    incident_in_policy_period: boolean;
    not_payable_reason?: string;
  };
  decision: {
    recommendation: Recommendation;
    recommended_payout_inr: number;
    confidence: number;
    headline: string;
    rationale: { point: string; source: string; impact: "supports" | "against" | "neutral" }[];
    next_steps: string[];
    fast_track_eligible: boolean;
    customer_language: string;
    customer_message_english: string;
    customer_message_local: string;
  };
  photo_meta: { file_id: string; name: string; taken_at: string | null }[];
};

export type FinalDecision = {
  action: Recommendation;
  amount: number;
  note: string;
  by: string;
  at: string;
  override: boolean;
  ai_recommendation: Recommendation;
  ai_amount: number;
  customer_message?: { english: string; local: string };
};

export type TimelineEntry = { at: string; kind: string; text: string; text_english?: string };
export type ChatMessage = { role: "user" | "assistant"; text: string; at: string };

export type Claim = {
  id: string;
  created_at: string;
  updated_at: string;
  reported_on: string;
  status: "queued" | "processing" | "review" | "approved" | "rejected" | "info_requested" | "investigating" | "error";
  channel: string;
  policy_number: string;
  claimant: { name: string; first_name: string; phone_masked: string; language: string; language_name: string };
  vehicle: { registration: string; make_model: string; year: number; colour: string };
  statement: string;
  transcript: { transcript: string; english: string; language: string } | null;
  files: ClaimFile[];
  trace: TraceStep[];
  timeline: TimelineEntry[];
  audit: { at: string; actor: string; action: string; detail: string }[];
  chat: { adjuster: ChatMessage[]; customer: ChatMessage[] };
  ai?: AI;
  model?: { engine: string; model: string; adjudicator: string; gemma: string | null };
  processing_seconds?: number;
  error?: string | null;
  final_decision?: FinalDecision;
  risk_level?: string;
  risk_score?: number;
};

export type ClaimRow = {
  id: string;
  created_at: string;
  updated_at: string;
  status: Claim["status"];
  claimant: string;
  language_name: string;
  vehicle: Claim["vehicle"];
  claimed_amount: number | null;
  recommended_payout: number | null;
  recommendation: Recommendation | null;
  risk_level: "low" | "medium" | "high" | null;
  risk_score: number | null;
  fast_track: boolean | null;
  processing_seconds: number | null;
  final_decision: FinalDecision | null;
  incident_type: string | null;
  headline: string | null;
};

export type PublicClaim = {
  id: string;
  status: Claim["status"];
  created_at: string;
  updated_at: string;
  claimant: Claim["claimant"];
  vehicle: Claim["vehicle"];
  progress: { label: string; status: TraceStep["status"] }[];
  timeline: TimelineEntry[];
  error?: string | null;
  files: { id: string; name: string; kind: string; url: string }[];
  final_decision?: FinalDecision | null;
  chat: ChatMessage[];
  summary?: {
    message_local: string;
    message_english: string;
    language: string;
    estimated_payout: number | null;
    estimate: { gross_total: number; depreciation_total: number; deductible: number; recommended_payout: number; zero_dep: boolean } | null;
    coverage: { item: string; status: string; reason: string; clause_ref: string }[];
    damaged_parts: { part_name: string; action: string }[];
  };
};

export type Insights = {
  claims_total: number;
  analysed: number;
  awaiting_decision: number;
  decided: number;
  avg_ai_seconds: number | null;
  avg_minutes_to_decide: number | null;
  agreement_rate: number | null;
  fast_track: number;
  risk: Record<string, number>;
  recommendations: Record<string, number>;
  amount_held_inr: number;
  amount_approved_inr: number;
  baseline: { avg_days_to_settle: number | null; past_claims: number; source: string };
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : body.message || msg;
    } catch {
      /* not JSON */
    }
    throw new ApiError(msg, res.status);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/api/health"),
  samples: () => request<SampleKit[]>("/api/demo/samples"),
  sampleFile: async (key: string, name: string, mime: string) => {
    const res = await fetch(`/api/demo/samples/${key}/files/${encodeURIComponent(name)}`);
    const blob = await res.blob();
    return new File([blob], name, { type: mime });
  },
  lookupPolicy: (q: string) => request<Policy>(`/api/policies/lookup?q=${encodeURIComponent(q)}`),
  transcribe: (audio: Blob, language: string) => {
    const fd = new FormData();
    fd.append("audio", audio, "voice-note.wav");
    fd.append("language", language);
    return request<{ language: string; language_code: string; transcript: string; english: string }>("/api/transcribe", {
      method: "POST",
      body: fd,
    });
  },
  createClaim: (fd: FormData) => request<{ claim_id: string }>("/api/claims", { method: "POST", body: fd }),
  claims: () => request<ClaimRow[]>("/api/claims"),
  claim: (id: string) => request<Claim>(`/api/claims/${id}`),
  publicClaim: (id: string) => request<PublicClaim>(`/api/claims/${id}/public`),
  rerun: (id: string) => request<{ ok: boolean }>(`/api/claims/${id}/rerun`, { method: "POST" }),
  decide: (id: string, body: { action: Recommendation; amount: number; note: string; adjuster: string }) =>
    request<{ ok: boolean; status: string }>(`/api/claims/${id}/decision`, json(body)),
  ask: (id: string, question: string, audience: "adjuster" | "customer") =>
    request<{ answer: string }>(`/api/claims/${id}/ask`, json({ question, audience })),
  insights: () => request<Insights>("/api/insights"),
  resetDemo: (process_samples: boolean) => request<{ seeded_on: string }>("/api/demo/reset", json({ process_samples })),
  processSamples: () => request<{ ok: boolean }>("/api/demo/process-samples", { method: "POST" }),
};

/** Subscribe to live claim updates (server-sent events). Returns an unsubscribe function. */
export function subscribeClaim<T>(id: string, audience: "adjuster" | "customer", onData: (data: T) => void): () => void {
  let es: EventSource | null = null;
  let stopped = false;
  let retry: number | undefined;
  const open = () => {
    es = new EventSource(`/api/claims/${id}/stream?audience=${audience}`);
    es.onmessage = (ev) => {
      try {
        onData(JSON.parse(ev.data) as T);
      } catch {
        /* ignore malformed frames */
      }
    };
    es.onerror = () => {
      es?.close();
      if (!stopped) retry = window.setTimeout(open, 2000);
    };
  };
  open();
  return () => {
    stopped = true;
    window.clearTimeout(retry);
    es?.close();
  };
}
