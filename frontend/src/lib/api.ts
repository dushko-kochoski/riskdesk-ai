const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
let authorizationHeader: string | null = null;

export type HealthResponse = {
  status: string;
  service: string;
};

export type AuthenticatedOperator = {
  actor: string;
  demo_mode: boolean;
};

export type DashboardSummary = {
  total_events: number;
  total_cases: number;
  open_cases: number;
  high_risk_cases: number;
  on_hold_cases: number;
  escalated_cases: number;
  cases_by_risk_level: Record<string, number>;
  cases_by_status: Record<string, number>;
  prevented_exposure_estimate: number;
  recent_audit_logs: AuditLog[];
};

export type AuditLog = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: string;
  created_at: string;
};

export type RiskCase = {
  id: number;
  event_id: number;
  player_id: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | string;
  recommended_action: string;
  triggered_rules: string[];
  status: string;
  version: number;
  created_at: string;
};

export type CaseFilters = {
  status?: string;
  riskLevel?: string;
  playerId?: string;
};

export type SimulatorScenario =
  | "normal_player"
  | "high_value_withdrawal_incomplete_kyc"
  | "bonus_abuse_attempt"
  | "high_risk_country_withdrawal";

export type SimulatorRunResponse = {
  scenario: SimulatorScenario;
  player_id: string;
  events_created: number;
  cases_created: number;
  event_ids: number[];
  case_ids: number[];
};

export type CaseDecisionAction = "hold" | "escalate" | "approve" | "close";

export type CaseDecisionResponse = {
  case_id: number;
  action: string;
  previous_status: string;
  new_status: string;
  actor: string;
  version: number;
  note: string | null;
  audit_log_id: number;
};

export type DemoResetResponse = {
  status: "reset_complete";
  deleted: {
    audit_logs: number;
    triggered_rules: number;
    cases: number;
    events: number;
  };
};

export type DemoSeedResponse = {
  status: "seed_complete";
  scenarios_run: number;
  events_created: number;
  cases_created: number;
  case_ids: number[];
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function encodeBasicCredentials(username: string, password: string) {
  const bytes = new TextEncoder().encode(`${username}:${password}`);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return `Basic ${window.btoa(binary)}`;
}

export function setOperatorCredentials(username: string, password: string) {
  authorizationHeader = encodeBasicCredentials(username, password);
}

export function clearOperatorCredentials() {
  authorizationHeader = null;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authorizationHeader ? { Authorization: authorizationHeader } : {}),
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getHealth() {
  return request<HealthResponse>("/api/healthz");
}

export function getAuthenticatedOperator() {
  return request<AuthenticatedOperator>("/api/v1/auth/me");
}

export function getDashboardSummary() {
  return request<DashboardSummary>("/api/v1/dashboard/summary");
}

export function getCases(filters: CaseFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.riskLevel) params.set("risk_level", filters.riskLevel);
  if (filters.playerId) params.set("player_id", filters.playerId);
  const query = params.toString();

  return request<RiskCase[]>(`/api/v1/cases${query ? `?${query}` : ""}`);
}

export function runSimulator(scenario: SimulatorScenario, playerId?: string) {
  return request<SimulatorRunResponse>("/api/v1/simulator/run", {
    method: "POST",
    body: JSON.stringify({ scenario, player_id: playerId }),
  });
}

export function submitCaseDecision(
  caseId: number,
  action: CaseDecisionAction,
  expectedVersion: number,
  note: string,
) {
  return request<CaseDecisionResponse>(`/api/v1/cases/${caseId}/decision`, {
    method: "POST",
    body: JSON.stringify({ action, expected_version: expectedVersion, note }),
  });
}

export function resetDemoData() {
  return request<DemoResetResponse>("/api/v1/demo/reset", {
    method: "POST",
  });
}

export function seedDemoData() {
  return request<DemoSeedResponse>("/api/v1/demo/seed", {
    method: "POST",
  });
}
