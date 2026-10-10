// ─────────────────────────────────────────────────────────────────────────────
// TypeScript interfaces exactly matching the FastAPI backend schemas
// ─────────────────────────────────────────────────────────────────────────────

export type UserRole = "ADMIN" | "EMPLOYEE";
export type WorkLocation = "OFFICE" | "WORK_FROM_HOME";
export type AttendanceStatus = "PRESENT" | "HALF_DAY" | "ABSENT" | "NOT_ATTENDED";

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  employee_id: number;
  role: UserRole;
}

export interface UserProfile {
  id: number;
  full_name: string;
  email: string;
  department: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Employee ──────────────────────────────────────────────────────────────────
export interface Employee {
  id: number;
  full_name: string;
  email: string;
  department: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmployeeCreateRequest {
  full_name: string;
  email: string;
  department: string;
  password: string;
  role: UserRole;
}

export interface EmployeeUpdateRequest {
  full_name?: string;
  department?: string;
  email?: string;
}

export interface EmployeeListResponse {
  total: number;
  page: number;
  page_size: number;
  employees: Employee[];
}

// ── Attendance ────────────────────────────────────────────────────────────────
export interface AttendanceRecord {
  id: number;
  employee_id: number;
  entry_time: string;
  exit_time: string | null;
  work_location: WorkLocation;
  working_hours: number | null;
  status: AttendanceStatus;
  created_at: string;
  updated_at: string;
}

export interface AttendanceListResponse {
  total: number;
  records: AttendanceRecord[];
}

export interface CheckInRequest {
  work_location: WorkLocation;
}

export interface AttendanceSummaryResponse {
  total_working_hours: number;
  average_working_hours: number;
  total_days_present: number;
  total_days_wfh: number;
  total_days_office: number;
}

// ── Compliance ────────────────────────────────────────────────────────────────
export interface ComplianceRecord {
  id: number;
  employee_id: number;
  week_start: string;
  week_end: string;
  attendance_days: number;
  total_working_hours: number;
  average_working_hours: number;
  is_compliant: boolean;
  violation_reasons: string[];
  evaluated_at: string;
}

export interface ComplianceViolation {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_email: string;
  week_start: string;
  week_end: string;
  attendance_days: number;
  total_working_hours: number;
  is_compliant: boolean;
  violation_reasons: string[];
  evaluated_at: string;
}

export interface ComplianceViolationListResponse {
  total: number;
  page: number;
  page_size: number;
  violations: ComplianceViolation[];
}

export interface ComplianceEvaluateResponse {
  evaluated_employees: number;
  compliant: number;
  non_compliant: number;
  notifications_queued: number;
}

// ── Reports ───────────────────────────────────────────────────────────────────
export interface ReportEmployeeRecord {
  employee_id: number;
  employee_name: string;
  department: string;
  total_days_present: number;
  total_working_hours: number;
  average_working_hours: number;
  office_days: number;
  wfh_days: number;
  is_compliant: boolean;
  compliance_pending?: boolean;
}

export interface AttendanceReportResponse {
  period: string;
  start_date: string;
  end_date: string;
  total_employees: number;
  employees: ReportEmployeeRecord[];
}
