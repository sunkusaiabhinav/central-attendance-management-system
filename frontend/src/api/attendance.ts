import apiClient from "./client";
import type {
  AttendanceListResponse,
  AttendanceRecord,
  AttendanceSummaryResponse,
  CheckInRequest,
} from "@/types";

export const attendanceApi = {
  /** POST /api/v1/attendance/check-in */
  checkIn: async (data: CheckInRequest): Promise<AttendanceRecord> => {
    const res = await apiClient.post<AttendanceRecord>(
      "/api/v1/attendance/check-in",
      data
    );
    return res.data;
  },

  /** POST /api/v1/attendance/check-out */
  checkOut: async (): Promise<AttendanceRecord> => {
    const res = await apiClient.post<AttendanceRecord>(
      "/api/v1/attendance/check-out"
    );
    return res.data;
  },

  /** GET /api/v1/attendance/me */
  myAttendance: async (params?: {
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<AttendanceListResponse> => {
    const res = await apiClient.get<AttendanceListResponse>(
      "/api/v1/attendance/me",
      { params }
    );
    return res.data;
  },

  /** GET /api/v1/attendance/{employee_id} */
  employeeAttendance: async (
    employeeId: number,
    params?: {
      start_date?: string;
      end_date?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<AttendanceListResponse> => {
    const res = await apiClient.get<AttendanceListResponse>(
      `/api/v1/attendance/${employeeId}`,
      { params }
    );
    return res.data;
  },

  /** GET /api/v1/attendance/{employee_id}/summary */
  summary: async (
    employeeId: number,
    params?: {
      start_date?: string;
      end_date?: string;
    }
  ): Promise<AttendanceSummaryResponse> => {
    const res = await apiClient.get<AttendanceSummaryResponse>(
      `/api/v1/attendance/${employeeId}/summary`,
      { params }
    );
    return res.data;
  },
};
