import apiClient from "./client";
import type {
  Employee,
  EmployeeCreateRequest,
  EmployeeListResponse,
  EmployeeUpdateRequest,
} from "@/types";

export const employeesApi = {
  /** GET /api/v1/employees */
  list: async (params?: {
    page?: number;
    page_size?: number;
    department?: string;
    is_active?: boolean;
  }): Promise<EmployeeListResponse> => {
    const res = await apiClient.get<EmployeeListResponse>("/api/v1/employees", {
      params,
    });
    return res.data;
  },

  /** GET /api/v1/employees/{id} */
  get: async (id: number): Promise<Employee> => {
    const res = await apiClient.get<Employee>(`/api/v1/employees/${id}`);
    return res.data;
  },

  /** POST /api/v1/employees */
  create: async (data: EmployeeCreateRequest): Promise<Employee> => {
    const res = await apiClient.post<Employee>("/api/v1/employees", data);
    return res.data;
  },

  /** PATCH /api/v1/employees/{id} */
  update: async (id: number, data: EmployeeUpdateRequest): Promise<Employee> => {
    const res = await apiClient.patch<Employee>(`/api/v1/employees/${id}`, data);
    return res.data;
  },

  /** PATCH /api/v1/employees/{id}/status */
  updateStatus: async (id: number, isActive: boolean): Promise<Employee> => {
    const res = await apiClient.patch<Employee>(
      `/api/v1/employees/${id}/status`,
      { is_active: isActive }
    );
    return res.data;
  },
};
