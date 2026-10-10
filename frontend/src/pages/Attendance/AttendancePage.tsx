import { useEffect, useState } from "react";
import {
  Download,
  Search,
  Briefcase,
  Laptop,
  Calendar,
} from "lucide-react";
import { employeesApi } from "@/api/employees";
import { attendanceApi } from "@/api/attendance";
import { formatDate, formatTime, formatHours, todayIST } from "@/utils";
import type { Employee, AttendanceRecord } from "@/types";

export function AttendancePage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [startDate, setStartDate] = useState(todayIST());
  const [endDate, setEndDate] = useState(todayIST());
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    employeesApi.list({ page: 1, page_size: 100 }).then((res) => {
      setEmployees(res.employees);
      if (res.employees.length > 0) {
        setSelectedEmployeeId(res.employees[0].id);
      }
    });
  }, []);

  const loadAttendance = async (empId: number) => {
    setIsLoading(true);
    try {
      const res = await attendanceApi.employeeAttendance(empId, {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        page: 1,
        page_size: 100,
      });
      setRecords(res.records);
    } catch (err) {
      console.error("Failed to load attendance", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedEmployeeId) {
      loadAttendance(selectedEmployeeId);
    }
  }, [selectedEmployeeId, startDate, endDate]);

  const filteredEmployees = employees.filter(
    (e) =>
      e.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const selectedEmployee = employees.find((e) => e.id === selectedEmployeeId);

  const exportCSV = () => {
    if (records.length === 0) return;
    const headers = ["Employee", "Date", "Entry Time", "Exit Time", "Location", "Hours", "Status"];
    const rows = records.map((r) => [
      selectedEmployee?.full_name ?? r.employee_id,
      formatDate(r.entry_time),
      formatTime(r.entry_time),
      formatTime(r.exit_time),
      r.work_location,
      r.working_hours ?? "0",
      r.status,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `attendance_${selectedEmployee?.full_name || "report"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Attendance <span className="text-gradient">Records</span>
          </h1>
          <p className="page-subtitle">
            Inspect check-in timestamps, working durations, and location telemetry
          </p>
        </div>
        <button
          onClick={exportCSV}
          disabled={records.length === 0}
          className="btn-secondary text-xs gap-1.5"
        >
          <Download className="w-3.5 h-3.5" />
          Export CSV
        </button>
      </div>

      {/* ── Filter Bar ── */}
      <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Calendar className="w-4 h-4 text-brand-400" />
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="input-field py-1.5 px-3 text-xs w-36"
            />
            <span className="text-slate-500 text-xs">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="input-field py-1.5 px-3 text-xs w-36"
            />
          </div>
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search employee or dept..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field py-1.5 pl-8 text-xs"
          />
        </div>
      </div>

      {/* ── Main Layout: Employee Selector + Attendance Log ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: Employee Selection List */}
        <div className="glass-card p-4 max-h-[600px] overflow-y-auto space-y-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Select Employee ({filteredEmployees.length})
          </p>
          {filteredEmployees.map((emp) => (
            <button
              key={emp.id}
              onClick={() => setSelectedEmployeeId(emp.id)}
              className={`w-full text-left p-3 rounded-xl transition-all duration-200 border text-xs flex items-center justify-between ${
                selectedEmployeeId === emp.id
                  ? "bg-brand-600/20 border-brand-500/40 text-brand-200 shadow-glow-sm"
                  : "bg-white/5 border-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              <div>
                <p className="font-semibold">{emp.full_name}</p>
                <p className="text-slate-500 text-[11px]">{emp.department}</p>
              </div>
              <span
                className={`w-2 h-2 rounded-full ${
                  emp.is_active ? "bg-emerald-400" : "bg-slate-500"
                }`}
              />
            </button>
          ))}
        </div>

        {/* Right: Selected Employee Attendance Records */}
        <div className="lg:col-span-3 table-container">
          <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-brand-600/20 text-brand-300 flex items-center justify-center font-bold">
                {selectedEmployee?.full_name?.charAt(0) ?? "E"}
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  {selectedEmployee?.full_name ?? "Employee Attendance"}
                </h2>
                <p className="text-xs text-slate-400">
                  {selectedEmployee?.email} · {selectedEmployee?.department}
                </p>
              </div>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              {records.length} records
            </span>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              <div className="w-6 h-6 border-2 border-brand-500/40 border-t-brand-500 rounded-full animate-spin mx-auto mb-2" />
              Loading records...
            </div>
          ) : records.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm">
              No attendance logs found for the selected time range.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Date</th>
                    <th className="table-header">Entry (Check-In)</th>
                    <th className="table-header">Exit (Check-Out)</th>
                    <th className="table-header">Location</th>
                    <th className="table-header">Duration</th>
                    <th className="table-header">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r) => (
                    <tr key={r.id} className="table-row">
                      <td className="table-cell font-medium text-slate-200">
                        {formatDate(r.entry_time)}
                      </td>
                      <td className="table-cell font-mono text-emerald-400">
                        {formatTime(r.entry_time)}
                      </td>
                      <td className="table-cell font-mono text-slate-300">
                        {r.exit_time ? formatTime(r.exit_time) : (
                          <span className="text-xs text-amber-400 italic">In Progress</span>
                        )}
                      </td>
                      <td className="table-cell">
                        {r.work_location === "OFFICE" ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded-md">
                            <Briefcase className="w-3 h-3" /> Office
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded-md">
                            <Laptop className="w-3 h-3" /> Remote
                          </span>
                        )}
                      </td>
                      <td className="table-cell font-mono">
                        {formatHours(r.working_hours)}
                      </td>
                      <td className="table-cell">
                        <span
                          className={`badge ${
                            r.status === "PRESENT"
                              ? "badge-success"
                              : r.status === "HALF_DAY"
                              ? "badge-warning"
                              : "badge-danger"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
