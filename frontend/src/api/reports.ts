import apiClient from "./client";
import type { AttendanceReportResponse } from "@/types";

export const reportsApi = {
  /** GET /api/v1/reports/attendance (ADMIN) */
  getReport: async (params: {
    period: "daily" | "weekly" | "monthly" | "yearly" | "custom";
    date?: string;
    year?: number;
    month?: number;
    start_date?: string;
    end_date?: string;
    department?: string;
    employee_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<AttendanceReportResponse> => {
    const res = await apiClient.get<AttendanceReportResponse>(
      "/api/v1/reports/attendance",
      { params }
    );
    return res.data;
  },
};
