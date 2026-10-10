import apiClient from "./client";
import type {
  ComplianceEvaluateResponse,
  ComplianceRecord,
  ComplianceViolationListResponse,
} from "@/types";

export const complianceApi = {
  /** GET /api/v1/compliance/me */
  myCompliance: async (weekStart?: string): Promise<ComplianceRecord[]> => {
    const res = await apiClient.get<ComplianceRecord[]>("/api/v1/compliance/me", {
      params: { week_start: weekStart },
    });
    return res.data;
  },

  /** GET /api/v1/compliance/violations (ADMIN) */
  listViolations: async (params?: {
    page?: number;
    page_size?: number;
    week_start?: string;
  }): Promise<ComplianceViolationListResponse> => {
    const res = await apiClient.get<ComplianceViolationListResponse>(
      "/api/v1/compliance/violations",
      { params }
    );
    return res.data;
  },

  /** GET /api/v1/compliance/{employee_id} */
  employeeCompliance: async (
    employeeId: number,
    weekStart?: string
  ): Promise<ComplianceRecord[]> => {
    const res = await apiClient.get<ComplianceRecord[]>(
      `/api/v1/compliance/${employeeId}`,
      { params: { week_start: weekStart } }
    );
    return res.data;
  },

  /** POST /api/v1/compliance/evaluate (ADMIN) */
  evaluate: async (
    weekStart: string,
    force = false
  ): Promise<ComplianceEvaluateResponse> => {
    const res = await apiClient.post<ComplianceEvaluateResponse>(
      "/api/v1/compliance/evaluate",
      { week_start: weekStart },
      { params: { force } }
    );
    return res.data;
  },

  /** POST /api/v1/compliance/send-warning-emails (ADMIN) */
  sendWarningEmails: async (
    weekStart: string,
    force = true
  ): Promise<{
    week_start: string;
    total_non_compliant: number;
    emails_sent: number;
    emails_failed: number;
  }> => {
    const res = await apiClient.post(
      "/api/v1/compliance/send-warning-emails",
      null,
      { params: { week_start: weekStart, force } }
    );
    return res.data;
  },
};
