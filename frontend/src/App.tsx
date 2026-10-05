import { useCallback, useEffect, useMemo, useState } from "react";

import {
  type AuditLog,
  type CaseDecisionAction,
  type CaseFilters,
  type DashboardSummary,
  type HealthResponse,
  type RiskCase,
  type SimulatorScenario,
  getCases,
  getDashboardSummary,
  getHealth,
  resetDemoData,
  runSimulator,
  seedDemoData,
  submitCaseDecision,
} from "./lib/api";

const simulatorScenarios: Array<{ label: string; value: SimulatorScenario; tone: string }> = [
  { label: "Normal Player", value: "normal_player", tone: "Baseline" },
  {
    label: "High Withdrawal + Incomplete KYC",
    value: "high_value_withdrawal_incomplete_kyc",
    tone: "Payments",
  },
  { label: "Bonus Abuse Attempt", value: "bonus_abuse_attempt", tone: "Bonus" },
  { label: "High-Risk Country Withdrawal", value: "high_risk_country_withdrawal", tone: "AML" },
];

const decisionActions: Array<{ label: string; value: CaseDecisionAction }> = [
  { label: "Hold", value: "hold" },
  { label: "Escalate", value: "escalate" },
  { label: "Approve", value: "approve" },
  { label: "Close", value: "close" },
];

const decisionNote = "Decision submitted from RiskDesk AI demo dashboard.";
const emptyCaseFilters: CaseFilters = { status: "", riskLevel: "", playerId: "" };

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [cases, setCases] = useState<RiskCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);
  const [draftFilters, setDraftFilters] = useState<CaseFilters>(emptyCaseFilters);
  const [appliedFilters, setAppliedFilters] = useState<CaseFilters>(emptyCaseFilters);

  const selectedCase = useMemo(
    () => cases.find((riskCase) => riskCase.id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );

  const loadDashboard = useCallback(async () => {
    setError(null);
    const [healthResult, summaryResult, casesResult] = await Promise.all([
      getHealth(),
      getDashboardSummary(),
      getCases(appliedFilters),
    ]);
    setHealth(healthResult);
    setSummary(summaryResult);
    setCases(casesResult);
    return casesResult;
  }, [appliedFilters]);

  useEffect(() => {
    setIsLoading(true);
    loadDashboard()
      .catch((caughtError: unknown) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load dashboard");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [loadDashboard]);

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedCaseId(null);
      }
    }

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  const summaryCards = useMemo(
    () => [
      { label: "Total Events", value: summary?.total_events ?? 0, accent: "text-slate-100" },
      { label: "Total Cases", value: summary?.total_cases ?? 0, accent: "text-slate-100" },
      { label: "Open Cases", value: summary?.open_cases ?? 0, accent: "text-sky-100" },
      { label: "High Risk", value: summary?.high_risk_cases ?? 0, accent: "text-red-100" },
      { label: "On Hold", value: summary?.on_hold_cases ?? 0, accent: "text-amber-100" },
      { label: "Escalated", value: summary?.escalated_cases ?? 0, accent: "text-red-100" },
    ],
    [summary],
  );

  async function handleSimulatorRun(scenario: SimulatorScenario) {
    setIsMutating(true);
    setError(null);
    try {
      const result = await runSimulator(scenario);
      setLastAction(
        `${result.events_created} events and ${result.cases_created} cases created for ${result.player_id}`,
      );
      await loadDashboard();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Simulator run failed");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleDemoReset() {
    setIsMutating(true);
    setError(null);
    try {
      const result = await resetDemoData();
      setSelectedCaseId(null);
      setLastAction(
        `Demo reset complete: removed ${result.deleted.events} events, ${result.deleted.cases} cases, and ${result.deleted.audit_logs} audit logs.`,
      );
      await loadDashboard();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Demo reset failed");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleDemoSeed() {
    setIsMutating(true);
    setError(null);
    try {
      const result = await seedDemoData();
      setSelectedCaseId(null);
      setLastAction(
        `Clean demo generated: ${result.events_created} events and ${result.cases_created} cases across ${result.scenarios_run} scenarios.`,
      );
      await loadDashboard();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Demo seed failed");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleManualRefresh() {
    setIsMutating(true);
    setError(null);
    try {
      await loadDashboard();
      setLastAction("Dashboard refreshed.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Dashboard refresh failed");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleDecision(caseId: number, action: CaseDecisionAction) {
    setIsMutating(true);
    setError(null);
    try {
      const result = await submitCaseDecision(caseId, action, "demo_analyst", decisionNote);
      setLastAction(`Case ${result.case_id} moved to ${formatToken(result.new_status)}`);
      const refreshedCases = await loadDashboard();
      if (!refreshedCases.some((riskCase) => riskCase.id === caseId)) {
        setSelectedCaseId(null);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Decision submission failed");
    } finally {
      setIsMutating(false);
    }
  }

  function handleFilterApply() {
    setSelectedCaseId(null);
    setAppliedFilters({
      status: draftFilters.status,
      riskLevel: draftFilters.riskLevel,
      playerId: draftFilters.playerId?.trim(),
    });
  }

  function handleFilterClear() {
    setSelectedCaseId(null);
    setDraftFilters(emptyCaseFilters);
    setAppliedFilters(emptyCaseFilters);
  }

  return (
    <main className="min-h-screen text-slate-100">
      <header className="border-b border-white/10 bg-ink-950/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-300">
              Risk Operations
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-semibold tracking-normal text-white">RiskDesk AI</h1>
              <span className="rounded-md border border-teal-300/20 bg-teal-300/10 px-2.5 py-1 text-xs font-semibold text-teal-100">
                Demo environment
              </span>
            </div>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Fraud, Payments & Bonus Abuse Review Copilot
            </p>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              Simulated iGaming events are evaluated through explainable rules, converted into
              review cases, and tracked with audit logs.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <BackendStatus health={health} error={error} isLoading={isLoading} />
            <button
              type="button"
              disabled={isMutating}
              onClick={() => void handleManualRefresh()}
              className="rounded-md border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-teal-300/50 hover:bg-teal-300/10"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {error ? (
          <div className="mb-5 rounded-md border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        ) : null}
        {lastAction ? (
          <div className="mb-5 rounded-md border border-teal-300/20 bg-teal-300/10 px-4 py-3 text-sm text-teal-100">
            {lastAction}
          </div>
        ) : null}

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          {summaryCards.map((card) => (
            <SummaryCard
              key={card.label}
              label={card.label}
              value={card.value}
              accent={card.accent}
            />
          ))}
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
          <ReportsSnapshot summary={summary} />
          <RecentActivity auditLogs={summary?.recent_audit_logs ?? []} />
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
          <div className="grid gap-5">
            <DemoControls
              isBusy={isMutating}
              onReset={handleDemoReset}
              onSeed={handleDemoSeed}
              onRefresh={handleManualRefresh}
            />
            <SimulatorPanel isBusy={isMutating} onRun={handleSimulatorRun} />
          </div>
          <CaseQueue
            cases={cases}
            filters={draftFilters}
            hasActiveFilters={Object.values(appliedFilters).some(Boolean)}
            isBusy={isLoading || isMutating}
            onApplyFilters={handleFilterApply}
            onClearFilters={handleFilterClear}
            onFiltersChange={setDraftFilters}
            onView={(riskCase) => setSelectedCaseId(riskCase.id)}
          />
        </section>
      </div>

      <CaseDetailDrawer
        riskCase={selectedCase}
        isBusy={isMutating}
        onClose={() => setSelectedCaseId(null)}
        onDecision={handleDecision}
      />
    </main>
  );
}

type DemoControlsProps = {
  isBusy: boolean;
  onReset: () => Promise<void>;
  onSeed: () => Promise<void>;
  onRefresh: () => Promise<void>;
};

function DemoControls({ isBusy, onReset, onSeed, onRefresh }: DemoControlsProps) {
  return (
    <section className="rounded-lg border border-white/10 bg-ink-900/80 p-4 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Demo Controls</h2>
          <p className="mt-1 text-sm text-slate-400">Reset or rebuild the local dataset.</p>
        </div>
        <span className="rounded-md border border-sky-300/20 bg-sky-300/10 px-2.5 py-1 text-xs font-medium text-sky-200">
          Local
        </span>
      </div>
      <div className="mt-4 grid gap-2.5">
        <button
          type="button"
          disabled={isBusy}
          onClick={() => void onSeed()}
          className="rounded-md border border-teal-300/30 bg-teal-300/10 px-3.5 py-3 text-left text-sm font-semibold text-teal-100 transition hover:border-teal-200/60 hover:bg-teal-300/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Generate Clean Demo
        </button>
        <button
          type="button"
          disabled={isBusy}
          onClick={() => void onReset()}
          className="rounded-md border border-red-300/25 bg-red-400/10 px-3.5 py-3 text-left text-sm font-semibold text-red-100 transition hover:border-red-200/50 hover:bg-red-400/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reset Demo Data
        </button>
        <button
          type="button"
          disabled={isBusy}
          onClick={() => void onRefresh()}
          className="rounded-md border border-white/10 bg-white/[0.04] px-3.5 py-3 text-left text-sm font-semibold text-slate-100 transition hover:border-teal-300/50 hover:bg-teal-300/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Refresh Dashboard
        </button>
      </div>
    </section>
  );
}

type BackendStatusProps = {
  health: HealthResponse | null;
  error: string | null;
  isLoading: boolean;
};

function BackendStatus({ health, error, isLoading }: BackendStatusProps) {
  const isOnline = health?.status === "ok" && !error;
  const label = isLoading ? "Checking backend" : isOnline ? "Backend online" : "Backend offline";

  return (
    <div className="flex items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300">
      <span
        className={`h-2.5 w-2.5 rounded-full ${
          isLoading ? "bg-amber-300" : isOnline ? "bg-emerald-400" : "bg-red-400"
        }`}
      />
      <span className="whitespace-nowrap">{label}</span>
    </div>
  );
}

type SummaryCardProps = {
  label: string;
  value: number;
  accent: string;
};

function SummaryCard({ label, value, accent }: SummaryCardProps) {
  return (
    <article className="rounded-lg border border-white/10 bg-white/[0.055] p-4 shadow-panel transition hover:border-white/15 hover:bg-white/[0.075]">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className={`mt-3 text-3xl font-semibold ${accent}`}>{value.toLocaleString()}</p>
    </article>
  );
}

type ReportsSnapshotProps = {
  summary: DashboardSummary | null;
};

function ReportsSnapshot({ summary }: ReportsSnapshotProps) {
  const riskRows = ["HIGH", "MEDIUM", "LOW"].map((label) => ({
    label,
    value: summary?.cases_by_risk_level[label] ?? 0,
  }));
  const statusRows = [
    "open",
    "on_hold",
    "escalated",
    "pending_kyc",
    "rejected",
    "false_positive",
    "closed",
    "resolved",
  ].map((label) => ({
    label,
    value: summary?.cases_by_status[label] ?? 0,
  }));

  return (
    <section className="rounded-lg border border-white/10 bg-ink-900/80 p-4 shadow-panel">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Reports Snapshot</h2>
          <p className="mt-1 text-sm text-slate-400">
            Lightweight portfolio view of queue composition and estimated exposure.
          </p>
        </div>
        <div className="rounded-lg border border-emerald-300/20 bg-emerald-400/10 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-emerald-200/80">
            Prevented Exposure
          </p>
          <p className="mt-2 text-2xl font-semibold text-emerald-100">
            {formatCurrency(summary?.prevented_exposure_estimate ?? 0)}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <BarGroup title="Cases by Risk Level" rows={riskRows} />
        <BarGroup title="Cases by Status" rows={statusRows} />
      </div>
    </section>
  );
}

type BarGroupProps = {
  title: string;
  rows: Array<{ label: string; value: number }>;
};

function BarGroup({ title, rows }: BarGroupProps) {
  const maxValue = Math.max(...rows.map((row) => row.value), 1);

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <div className="mt-4 grid gap-3">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
              <span className="font-medium text-slate-300">{formatToken(row.label)}</span>
              <span className="font-mono text-slate-500">{row.value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-teal-300/70"
                style={{ width: `${Math.max((row.value / maxValue) * 100, row.value ? 8 : 0)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

type RecentActivityProps = {
  auditLogs: AuditLog[];
};

function RecentActivity({ auditLogs }: RecentActivityProps) {
  return (
    <section className="rounded-lg border border-white/10 bg-ink-900/80 p-4 shadow-panel">
      <div>
        <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
        <p className="mt-1 text-sm text-slate-400">Latest audit trail events.</p>
      </div>

      <div className="mt-5 grid gap-3">
        {auditLogs.length === 0 ? (
          <div className="rounded-md border border-white/10 bg-white/[0.035] px-4 py-6 text-sm text-slate-400">
            No recent activity yet.
          </div>
        ) : (
          auditLogs.map((auditLog) => (
            <article
              key={auditLog.id}
              className="rounded-md border border-white/10 bg-white/[0.035] px-3 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-100">
                    {formatAuditAction(auditLog.action)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {auditLog.entity_type}{" "}
                    {auditLog.entity_id === null ? "" : `#${auditLog.entity_id}`}
                  </p>
                </div>
                <time className="whitespace-nowrap text-xs text-slate-500">
                  {formatShortDate(auditLog.created_at)}
                </time>
              </div>
              {auditLog.details ? (
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">
                  {formatAuditDetails(auditLog.details)}
                </p>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );
}

type SimulatorPanelProps = {
  isBusy: boolean;
  onRun: (scenario: SimulatorScenario) => Promise<void>;
};

function SimulatorPanel({ isBusy, onRun }: SimulatorPanelProps) {
  return (
    <section className="rounded-lg border border-white/10 bg-ink-900/80 p-4 shadow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Simulator</h2>
          <p className="mt-1 text-sm text-slate-400">Generate casino risk events.</p>
        </div>
        <span className="rounded-md border border-teal-300/20 bg-teal-300/10 px-2.5 py-1 text-xs font-medium text-teal-200">
          Demo
        </span>
      </div>
      <div className="mt-4 grid gap-2.5">
        {simulatorScenarios.map((scenario) => (
          <button
            key={scenario.value}
            type="button"
            disabled={isBusy}
            onClick={() => void onRun(scenario.value)}
            className="group rounded-md border border-white/10 bg-white/[0.04] px-3.5 py-3 text-left transition hover:border-teal-300/50 hover:bg-teal-300/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-slate-100">{scenario.label}</span>
              <span className="whitespace-nowrap rounded bg-white/[0.06] px-2 py-1 text-xs font-medium text-slate-400 group-hover:text-teal-200">
                {scenario.tone}
              </span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

type CaseQueueProps = {
  cases: RiskCase[];
  filters: CaseFilters;
  hasActiveFilters: boolean;
  isBusy: boolean;
  onApplyFilters: () => void;
  onClearFilters: () => void;
  onFiltersChange: (filters: CaseFilters) => void;
  onView: (riskCase: RiskCase) => void;
};

function CaseQueue({
  cases,
  filters,
  hasActiveFilters,
  isBusy,
  onApplyFilters,
  onClearFilters,
  onFiltersChange,
  onView,
}: CaseQueueProps) {
  return (
    <section className="overflow-hidden rounded-lg border border-white/10 bg-ink-900/80 shadow-panel">
      <div className="border-b border-white/10 px-4 py-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Case Queue</h2>
          <p className="mt-1 text-sm text-slate-400">
            {cases.length} {hasActiveFilters ? "matching" : "total"} {cases.length === 1 ? "case" : "cases"}
          </p>
        </div>
        <form
          className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_160px_auto] md:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            onApplyFilters();
          }}
        >
          <label className="grid gap-1.5 text-xs font-medium text-slate-400">
            Player ID
            <input
              type="search"
              value={filters.playerId ?? ""}
              onChange={(event) => onFiltersChange({ ...filters, playerId: event.target.value })}
              placeholder="e.g. plr_sim_0001"
              className="min-w-0 rounded-md border border-white/10 bg-ink-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-teal-300/60 focus:ring-2 focus:ring-teal-300/15"
            />
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-slate-400">
            Risk level
            <select
              value={filters.riskLevel ?? ""}
              onChange={(event) => onFiltersChange({ ...filters, riskLevel: event.target.value })}
              className="rounded-md border border-white/10 bg-ink-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-teal-300/60 focus:ring-2 focus:ring-teal-300/15"
            >
              <option value="">All risks</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-slate-400">
            Status
            <select
              value={filters.status ?? ""}
              onChange={(event) => onFiltersChange({ ...filters, status: event.target.value })}
              className="rounded-md border border-white/10 bg-ink-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-teal-300/60 focus:ring-2 focus:ring-teal-300/15"
            >
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="on_hold">On hold</option>
              <option value="escalated">Escalated</option>
              <option value="pending_kyc">Pending KYC</option>
              <option value="rejected">Rejected</option>
              <option value="false_positive">False positive</option>
              <option value="closed">Closed</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isBusy}
              className="flex-1 rounded-md border border-teal-300/30 bg-teal-300/10 px-3.5 py-2.5 text-sm font-semibold text-teal-100 transition hover:border-teal-200/60 hover:bg-teal-300/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Apply
            </button>
            <button
              type="button"
              disabled={isBusy || (!hasActiveFilters && !Object.values(filters).some(Boolean))}
              onClick={onClearFilters}
              className="rounded-md border border-white/10 bg-white/[0.04] px-3.5 py-2.5 text-sm font-semibold text-slate-300 transition hover:border-white/20 hover:bg-white/[0.07] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Clear
            </button>
          </div>
        </form>
      </div>

      <div className="hidden lg:block">
        <table className="w-full table-fixed border-collapse text-left text-sm">
          <colgroup>
            <col className="w-[7%]" />
            <col className="w-[19%]" />
            <col className="w-[12%]" />
            <col className="w-[8%]" />
            <col className="w-[18%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[8%]" />
          </colgroup>
          <thead className="bg-white/[0.035] text-xs uppercase tracking-[0.1em] text-slate-500">
            <tr>
              <th className="px-3 py-3 font-medium">ID</th>
              <th className="px-3 py-3 font-medium">Player</th>
              <th className="px-3 py-3 font-medium">Risk</th>
              <th className="px-3 py-3 font-medium">Score</th>
              <th className="px-3 py-3 font-medium">Action</th>
              <th className="px-3 py-3 font-medium">Status</th>
              <th className="px-3 py-3 font-medium">Created</th>
              <th className="px-3 py-3 text-right font-medium">View</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {cases.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-slate-400" colSpan={8}>
                  {hasActiveFilters
                    ? "No cases match these filters. Clear or adjust the criteria."
                    : "No cases in queue. Generate clean demo data to populate the dashboard."}
                </td>
              </tr>
            ) : (
              cases.map((riskCase) => (
                <tr
                  key={riskCase.id}
                  className="text-slate-300 transition hover:bg-white/[0.035]"
                >
                  <td className="px-3 py-3 font-mono text-slate-400">#{riskCase.id}</td>
                  <td className="truncate px-3 py-3 font-medium text-slate-100">
                    {riskCase.player_id}
                  </td>
                  <td className="px-3 py-3">
                    <RiskBadge level={riskCase.risk_level} />
                  </td>
                  <td className="px-3 py-3">{riskCase.risk_score}</td>
                  <td className="truncate px-3 py-3">
                    {formatToken(riskCase.recommended_action)}
                  </td>
                  <td className="px-3 py-3">
                    <StatusBadge status={riskCase.status} />
                  </td>
                  <td className="truncate px-3 py-3 text-slate-400">
                    {formatShortDate(riskCase.created_at)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => onView(riskCase)}
                      className="rounded-md border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-slate-100 transition hover:border-teal-300/50 hover:bg-teal-300/10"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 p-4 lg:hidden">
        {cases.length === 0 ? (
          <div className="rounded-md border border-white/10 bg-white/[0.035] px-4 py-8 text-center text-sm text-slate-400">
            {hasActiveFilters
              ? "No cases match these filters. Clear or adjust the criteria."
              : "No cases in queue. Generate clean demo data to populate the dashboard."}
          </div>
        ) : (
          cases.map((riskCase) => (
            <button
              key={riskCase.id}
              type="button"
              onClick={() => onView(riskCase)}
              className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-left transition hover:border-teal-300/40 hover:bg-teal-300/10"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-mono text-xs text-slate-500">#{riskCase.id}</p>
                  <p className="mt-1 truncate text-sm font-semibold text-white">
                    {riskCase.player_id}
                  </p>
                </div>
                <RiskBadge level={riskCase.risk_level} />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <StatusBadge status={riskCase.status} />
                <span className="text-xs text-slate-500">{formatShortDate(riskCase.created_at)}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

type CaseDetailDrawerProps = {
  riskCase: RiskCase | null;
  isBusy: boolean;
  onClose: () => void;
  onDecision: (caseId: number, action: CaseDecisionAction) => Promise<void>;
};

function CaseDetailDrawer({ riskCase, isBusy, onClose, onDecision }: CaseDetailDrawerProps) {
  return (
    <div
      className={`fixed inset-0 z-50 transition ${
        riskCase ? "pointer-events-auto" : "pointer-events-none"
      }`}
      aria-hidden={!riskCase}
    >
      <button
        type="button"
        aria-label="Close case detail"
        onClick={onClose}
        className={`absolute inset-0 bg-black/55 transition-opacity ${
          riskCase ? "opacity-100" : "opacity-0"
        }`}
      />
      <aside
        className={`absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-white/10 bg-ink-900 shadow-panel transition-transform duration-200 sm:w-[520px] ${
          riskCase ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {riskCase ? (
          <>
            <div className="border-b border-white/10 px-5 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-xs text-slate-500">CASE #{riskCase.id}</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">{riskCase.player_id}</h2>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-sm font-medium text-slate-200 transition hover:border-white/20 hover:bg-white/[0.08]"
                >
                  Close
                </button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <RiskBadge level={riskCase.risk_level} />
                <StatusBadge status={riskCase.status} />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <DetailMetric label="Risk Score" value={riskCase.risk_score.toString()} />
                <DetailMetric label="Recommended Action" value={formatToken(riskCase.recommended_action)} />
                <DetailMetric label="Created At" value={formatDate(riskCase.created_at)} />
                <DetailMetric label="Event ID" value={`#${riskCase.event_id}`} />
              </div>

              <section className="mt-6">
                <h3 className="text-sm font-semibold text-white">Triggered Rules</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {riskCase.triggered_rules.length ? (
                    riskCase.triggered_rules.map((rule) => (
                      <span
                        key={rule}
                        className="rounded-md border border-white/10 bg-white/[0.045] px-2.5 py-1.5 text-xs font-medium text-slate-200"
                      >
                        {formatToken(rule)}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-slate-500">No triggered rules.</span>
                  )}
                </div>
              </section>
            </div>

            <div className="border-t border-white/10 p-5">
              <p className="mb-3 text-sm font-semibold text-white">Submit Decision</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {decisionActions.map((action) => (
                  <button
                    key={action.value}
                    type="button"
                    disabled={isBusy}
                    onClick={() => void onDecision(riskCase.id, action.value)}
                    className="rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-sm font-semibold text-slate-100 transition hover:border-teal-300/50 hover:bg-teal-300/10 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </aside>
    </div>
  );
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="mt-2 break-words text-sm font-medium text-slate-100">{value}</p>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const className =
    level === "HIGH"
      ? "border-red-400/30 bg-red-500/15 text-red-100"
      : level === "MEDIUM"
        ? "border-amber-300/30 bg-amber-400/15 text-amber-100"
        : "border-emerald-300/30 bg-emerald-400/15 text-emerald-100";

  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-md border px-2.5 py-1 text-xs font-semibold ${className}`}
    >
      {level}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const statusStyles: Record<string, string> = {
    open: "border-sky-300/30 bg-sky-400/15 text-sky-100",
    on_hold: "border-amber-300/30 bg-amber-400/15 text-amber-100",
    escalated: "border-red-400/30 bg-red-500/15 text-red-100",
    pending_kyc: "border-violet-300/30 bg-violet-400/15 text-violet-100",
    rejected: "border-rose-300/30 bg-rose-400/15 text-rose-100",
    false_positive: "border-emerald-300/30 bg-emerald-400/15 text-emerald-100",
    closed: "border-slate-300/20 bg-slate-300/10 text-slate-200",
    resolved: "border-teal-300/30 bg-teal-400/15 text-teal-100",
  };
  const className = statusStyles[status] ?? "border-slate-300/20 bg-slate-300/10 text-slate-200";

  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-md border px-2.5 py-1 text-xs font-medium ${className}`}
    >
      {formatToken(status)}
    </span>
  );
}

function formatToken(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatShortDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatAuditAction(action: string) {
  const labels: Record<string, string> = {
    event_received: "Event received",
    risk_evaluated: "Risk evaluated",
    case_created: "Case created",
    case_decision_recorded: "Case decision recorded",
  };
  return labels[action] ?? formatToken(action);
}

function formatAuditDetails(details: string) {
  try {
    const parsed = JSON.parse(details) as {
      action?: string;
      analyst?: string;
      new_status?: string;
      note?: string | null;
    };
    if (parsed.action && parsed.new_status) {
      return `${formatToken(parsed.action)} by ${parsed.analyst ?? "analyst"} -> ${formatToken(
        parsed.new_status,
      )}${parsed.note ? `: ${parsed.note}` : ""}`;
    }
  } catch {
    return details;
  }

  return details;
}

export default App;
