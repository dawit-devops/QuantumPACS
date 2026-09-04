import { request } from "./client";

// R2-02-07/09: report-template library + versioning.

export interface ReportTemplate {
  id: string;
  name: string;
  modality: string;
  body_part?: string;
  findings_template?: string;
  impression_template?: string;
  is_default?: boolean;
}

export interface TemplateVersion {
  id?: string;
  version_number: number;
  findings_template?: string;
  impression_template?: string;
  published_by?: string;
  published_at?: string;
}

const unwrap = async <T,>(p: Promise<{ data: T[] }>): Promise<T[]> =>
  (await p).data ?? [];

export const listReportTemplates = (
  modality?: string,
): Promise<ReportTemplate[]> =>
  unwrap<ReportTemplate>(
    request<{ data: ReportTemplate[] }>("ris/report-templates", {
      query: modality ? { modality } : {},
    }),
  );

export const listTemplateVersions = (
  id: string,
): Promise<TemplateVersion[]> =>
  unwrap<TemplateVersion>(
    request<{ data: TemplateVersion[] }>(
      `ris/report-templates/${id}/versions`,
    ),
  );

export const publishTemplateVersion = (
  id: string,
  body: { findings: string; impression: string },
): Promise<{ id: string; version_number: number }> =>
  request(`ris/report-templates/${id}/publish`, { method: "POST", data: body });

export const rollbackTemplateVersion = (
  id: string,
  version: number,
): Promise<{ id: string; version_number: number }> =>
  request(`ris/report-templates/${id}/rollback`, {
    method: "POST",
    data: { version },
  });
