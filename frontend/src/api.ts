import type {
  AuditEvent,
  Control,
  Evaluation,
  Evidence,
  Finding,
  FindingLineage,
  HealthResponse,
  Mapping,
  MappingLineage,
  MediaCase,
  Overview,
  ReportExport,
  Requirement,
  RequirementLineage,
  RegistrySync,
  Source,
  SourceSnapshotSummary,
  VerifiedExtraction,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    let detail = `API request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // A non-JSON proxy error still returns a useful HTTP status above.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

function mutation<T>(path: string, body: unknown, reviewerId?: string): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Idempotency-Key": crypto.randomUUID(),
  };
  if (reviewerId) headers["X-Reviewer-Id"] = reviewerId;
  return request<T>(path, { method: "POST", headers, body: JSON.stringify(body) });
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  overview: () => request<Overview>("/overview"),
  auditEvents: () => request<AuditEvent[]>("/audit-events?limit=25"),
  sources: () => request<Source[]>("/sources"),
  latestSourceSnapshots: () => request<SourceSnapshotSummary[]>("/source-snapshots/latest"),
  sourceSnapshots: (id: string) => request<SourceSnapshotSummary[]>(`/sources/${id}/snapshots`),
  syncRegistry: () => mutation<RegistrySync>("/sources/sync-registry", {}),
  refreshSource: (id: string) => mutation(`/sources/${id}/refresh`, {}),
  extractVerifiedRequirements: (snapshotId: string) =>
    mutation<VerifiedExtraction>(
      `/source-snapshots/${snapshotId}/extract-verified-requirements`,
      {},
    ),
  requirements: () => request<Requirement[]>("/requirements"),
  requirementLineage: () => request<RequirementLineage[]>("/requirements/lineage"),
  reviewRequirement: (id: string, disposition: string, rationale: string, reviewerId: string) =>
    mutation<Requirement>(`/requirements/${id}/review`, { disposition, rationale }, reviewerId),
  controls: () => request<Control[]>("/controls"),
  mappings: () => request<Mapping[]>("/mappings"),
  mappingLineage: () => request<MappingLineage[]>("/mappings/lineage"),
  createMapping: (requirementId: string, controlId: string, rationale: string) =>
    mutation<Mapping>("/mappings", {
      requirement_id: requirementId,
      control_id: controlId,
      rationale,
      provider: "human-authored",
    }),
  reviewMapping: (id: string, disposition: string, rationale: string, reviewerId: string) =>
    mutation<Mapping>(`/mappings/${id}/review`, { disposition, rationale }, reviewerId),
  cases: () => request<MediaCase[]>("/cases"),
  analyzeCase: (id: string) => mutation(`/cases/${id}/analyze?mode=async`, {}),
  evidence: (id: string) => request<Evidence[]>(`/cases/${id}/evidence`),
  findings: () => request<Finding[]>("/findings"),
  findingLineage: () => request<FindingLineage[]>("/findings/lineage"),
  reviewFinding: (id: string, disposition: string, rationale: string, reviewerId: string) =>
    mutation<Finding>(`/findings/${id}/review`, { disposition, rationale }, reviewerId),
  evaluations: () => request<Evaluation[]>("/evaluations"),
  runEvaluation: () => mutation<{ status: string; job_id: string }>("/evaluations/run", {}),
  reports: () => request<ReportExport[]>("/reports"),
  exportReport: (caseId: string, formats: string[]) =>
    mutation<ReportExport[]>(`/reports/${caseId}/export`, { formats }),
};
