import apiClient from "./client";
import type { LoginRequest, TokenResponse, UserProfile } from "@/types";

export const authApi = {
  /** POST /api/v1/auth/login → JWT token and employee_id */
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const formData = new FormData();
    formData.append("username", data.email);
    formData.append("password", data.password);
    const res = await apiClient.post<TokenResponse>(
      "/api/v1/auth/login",
      formData,
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );
    return res.data;
  },

  /** GET /api/v1/employees/{id} → Get full profile for logged-in user */
  getProfile: async (employeeId: number): Promise<UserProfile> => {
    const res = await apiClient.get<UserProfile>(`/api/v1/employees/${employeeId}`);
    return res.data;
  },
};
