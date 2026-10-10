import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute, PublicRoute, AdminRoute } from "@/components/ProtectedRoute";
import { DashboardLayout } from "@/components/DashboardLayout";
import { LoginPage } from "@/pages/Login/LoginPage";
import { DashboardPage } from "@/pages/Dashboard/DashboardPage";
import { AttendancePage } from "@/pages/Attendance/AttendancePage";
import { EmployeesPage } from "@/pages/Employees/EmployeesPage";
import { ReportsPage } from "@/pages/Reports/ReportsPage";
import { CompliancePage } from "@/pages/Compliance/CompliancePage";
import { MyAttendancePage } from "@/pages/MyAttendance/MyAttendancePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login Route */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        {/* Authenticated Dashboard Shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            {/* Admin-only Routes */}
            <Route element={<AdminRoute />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/attendance" element={<AttendancePage />} />
              <Route path="/employees" element={<EmployeesPage />} />
              <Route path="/reports" element={<ReportsPage />} />
            </Route>

            {/* Shared & Employee Routes */}
            <Route path="/compliance" element={<CompliancePage />} />
            <Route path="/my-attendance" element={<MyAttendancePage />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
