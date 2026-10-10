import { useEffect, useState } from "react";
import {
  Download,
  FileSpreadsheet,
} from "lucide-react";
import { reportsApi } from "@/api/reports";
import { formatHours, todayIST } from "@/utils";
import type { AttendanceReportResponse } from "@/types";

type PeriodType = "daily" | "weekly" | "monthly" | "yearly" | "custom";

export function ReportsPage() {
  const [period, setPeriod] = useState<PeriodType>("monthly");
  const [date, setDate] = useState(todayIST());
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [startDate, setStartDate] = useState(todayIST());
  const [endDate, setEndDate] = useState(todayIST());

  const [report, setReport] = useState<AttendanceReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReport = async () => {
    setIsLoading(true);
    try {
      const res = await reportsApi.getReport({
        period,
        date: period === "daily" || period === "weekly" ? date : undefined,
        year: period === "monthly" || period === "yearly" ? year : undefined,
        month: period === "monthly" ? month : undefined,
        start_date: period === "custom" ? startDate : undefined,
        end_date: period === "custom" ? endDate : undefined,
        page: 1,
        page_size: 100,
      });
      setReport(res);
    } catch (err) {
      console.error("Failed to fetch report", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [period, date, year, month, startDate, endDate]);

  const exportCSV = () => {
    if (!report || report.employees.length === 0) return;
    const headers = [
      "Employee ID",
      "Employee Name",
      "Department",
      "Days Present",
      "Office Days",
      "WFH Days",
      "Total Hours",
      "Avg Hours/Day",
      "Compliance Status",
    ];

    const rows = report.employees.map((e) => [
      e.employee_id,
      e.employee_name,
      e.department,
      e.total_days_present,
      e.office_days,
      e.wfh_days,
      e.total_working_hours,
      e.average_working_hours,
      e.is_compliant ? "COMPLIANT" : e.compliance_pending ? "PENDING" : "NON_COMPLIANT",
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `attendance_report_${period}_${todayIST()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const employees = report?.employees ?? [];
  const compliantCount = employees.filter((e) => e.is_compliant).length;
  const totalHoursWorked = employees.reduce((acc, e) => acc + e.total_working_hours, 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Unified <span className="text-gradient">Attendance Reports</span>
          </h1>
          <p className="page-subtitle">
            Company-wide rollups across Daily, Weekly, Monthly, Yearly, and Custom intervals
          </p>
        </div>
        <button
          onClick={exportCSV}
          disabled={employees.length === 0}
          className="btn-secondary text-xs gap-1.5"
        >
          <Download className="w-3.5 h-3.5" />
          Export Report
        </button>
      </div>

      {/* ── Period Selector & Date Controls ── */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {(["daily", "weekly", "monthly", "yearly", "custom"] as PeriodType[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all duration-200 ${
                period === p
                  ? "bg-brand-600 text-white shadow-glow-sm"
                  : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Dynamic Controls based on Period */}
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-white/5">
          {(period === "daily" || period === "weekly") && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Reference Date:</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="input-field py-1.5 px-3 text-xs w-40"
              />
            </div>
          )}

          {period === "monthly" && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Year:</span>
                <input
                  type="number"
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className="input-field py-1.5 px-3 text-xs w-24"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Month:</span>
                <select
                  value={month}
                  onChange={(e) => setMonth(Number(e.target.value))}
                  className="input-field py-1.5 px-3 text-xs w-32"
                >
                  {[
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                  ].map((m, idx) => (
                    <option key={m} value={idx + 1}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {period === "yearly" && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Year:</span>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="input-field py-1.5 px-3 text-xs w-28"
              />
            </div>
          )}

          {period === "custom" && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">From:</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input-field py-1.5 px-3 text-xs w-36"
              />
              <span className="text-xs text-slate-400">To:</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input-field py-1.5 px-3 text-xs w-36"
              />
            </div>
          )}

          {report && (
            <div className="ml-auto text-xs text-slate-400">
              Range: <span className="font-mono text-slate-200">{report.start_date}</span> to{" "}
              <span className="font-mono text-slate-200">{report.end_date}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Summary Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="glass-card p-4">
          <p className="text-xs text-slate-400">Total Employees</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">{employees.length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs text-slate-400">Total Working Hours</p>
          <p className="text-2xl font-bold text-brand-400 mt-1">{formatHours(totalHoursWorked)}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs text-slate-400">Compliant Workforce</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">
            {compliantCount}{" "}
            <span className="text-xs font-normal text-slate-500">
              ({employees.length > 0 ? Math.round((compliantCount / employees.length) * 100) : 0}%)
            </span>
          </p>
        </div>
      </div>

      {/* ── Report Table ── */}
      <div className="table-container">
        <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-brand-400" />
            Report Roster ({employees.length})
          </h2>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="w-6 h-6 border-2 border-brand-500/40 border-t-brand-500 rounded-full animate-spin mx-auto mb-2" />
            Compiling report dataset...
          </div>
        ) : employees.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No records found for the requested period.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Employee</th>
                  <th className="table-header">Department</th>
                  <th className="table-header">Days Present</th>
                  <th className="table-header">Office vs Remote</th>
                  <th className="table-header">Total Hours</th>
                  <th className="table-header">Avg Hours/Day</th>
                  <th className="table-header">Compliance</th>
                </tr>
              </thead>
              <tbody>
                {employees.map((row) => (
                  <tr key={row.employee_id} className="table-row">
                    <td className="table-cell font-medium text-slate-200">
                      {row.employee_name}
                    </td>
                    <td className="table-cell text-slate-400">{row.department}</td>
                    <td className="table-cell font-mono">{row.total_days_present}</td>
                    <td className="table-cell text-xs">
                      <span className="text-emerald-400">{row.office_days} Off</span> ·{" "}
                      <span className="text-blue-400">{row.wfh_days} Rem</span>
                    </td>
                    <td className="table-cell font-mono font-medium text-slate-200">
                      {formatHours(row.total_working_hours)}
                    </td>
                    <td className="table-cell font-mono text-slate-400">
                      {formatHours(row.average_working_hours)}
                    </td>
                    <td className="table-cell">
                      {row.is_compliant ? (
                        <span className="badge-success">Compliant</span>
                      ) : row.compliance_pending ? (
                        <span className="badge-warning">Pending</span>
                      ) : (
                        <span className="badge-danger">Non-Compliant</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
