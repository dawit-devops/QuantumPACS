import { request } from "./client";

export interface DicomwebAdminInfo {
  qido?: {
    enabled: boolean;
    endpoints: Array<Record<string, unknown>>;
    search_params: Array<Record<string, unknown>>;
    response_format: string;
  };
  [key: string]: unknown;
}

export const getDicomwebAdmin = (): Promise<DicomwebAdminInfo> =>
  request<DicomwebAdminInfo>("dicomweb/admin");
