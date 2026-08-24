import { request } from "../helpers";

// ---- Types ----

export interface RejectByModality {
  modality: string;
  total: number;
  fails: number;
  reject_rate: number;
}

export interface RejectByTech {
  tech: string;
  total: number;
  fails: number;
  reject_rate: number;
}

export interface RejectByProtocol {
  protocol_name: string;
  modality: string;
  total: number;
  fails: number;
  reject_rate: number;
}

export interface RejectByDiscrepancy {
  discrepancy_level: string;
  n: number;
}

export interface RejectAnalysisData {
  by_modality: RejectByModality[];
  by_technologist: RejectByTech[];
  by_protocol: RejectByProtocol[];
  by_discrepancy: RejectByDiscrepancy[];
}

export interface DoseByModality {
  modality: string;
  n: number;
  avg_dlp: number;
  max_dlp: number;
  avg_ctdivol: number;
  max_ctdivol: number;
  acr_benchmark_dlp: number | null;
  acr_benchmark_ctdivol: number | null;
  dlp_exceedances: number;
}

export interface DoseExceedance {
  protocol_name: string;
  modality: string;
  acr_benchmark_dlp: number;
  dose_dlp: number;
  dose_ctdivol: number;
  accession_number: string;
  reviewed_at: string;
}

export interface DoseTrackingData {
  by_modality: DoseByModality[];
  exceedances: DoseExceedance[];
}

export interface TechMetric {
  tech: string;
  total_reviewed: number;
  passed: number;
  failed: number;
  reject_rate: number;
  avg_dlp: number;
  protocol_adherence_pct: number;
}

export interface ProtocolCompliance {
  protocol_id: string;
  protocol_name: string;
  modality: string;
  body_part: string;
  acr_benchmark_dlp: number | null;
  acr_benchmark_ctdivol: number | null;
  total_reviews: number;
  passed: number;
  failed: number;
  compliance_pct: number;
  avg_dlp: number;
  avg_ctdivol: number;
}

export interface TrendPoint {
  period: string;
  total: number;
  passed: number;
  failed: number;
  reject_rate: number;
  avg_dlp: number;
  avg_ctdivol: number;
}

// ---- API calls ----

export async function getRejectAnalysis(): Promise<RejectAnalysisData> {
  const res = await request("qa/reject-analysis");
  return res.data;
}

export async function getDoseTracking(): Promise<DoseTrackingData> {
  const res = await request("qa/dose-tracking");
  return res.data;
}

export async function getTechMetrics(): Promise<TechMetric[]> {
  const res = await request("qa/tech-metrics");
  return res.data;
}

export async function getProtocolCompliance(): Promise<ProtocolCompliance[]> {
  const res = await request("qa/protocol-compliance");
  return res.data;
}

export async function getQATrends(
  granularity: "daily" | "weekly" | "monthly" = "daily",
): Promise<{ data: TrendPoint[]; granularity: string }> {
  const res = await request("qa/trends", { query: { granularity } });
  return res;
}
