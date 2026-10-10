import { useEffect, useState } from "react";
import {
  Clock,
  LogIn,
  LogOut,
  Briefcase,
  Laptop,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { attendanceApi } from "@/api/attendance";
import { useAuthStore } from "@/store/authStore";
import { formatDate, formatTime, formatHours } from "@/utils";
import type { AttendanceRecord, AttendanceSummaryResponse, WorkLocation } from "@/types";

export function MyAttendancePage() {
  const { user } = useAuthStore();
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [summary, setSummary] = useState<AttendanceSummaryResponse | null>(null);
  const [location, setLocation] = useState<WorkLocation>("OFFICE");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchMyData = async () => {
    setIsLoading(true);
    try {
      const [recRes, sumRes] = await Promise.allSettled([
        attendanceApi.myAttendance({ page: 1, page_size: 50 }),
        user ? attendanceApi.summary(user.id) : Promise.reject(),
      ]);

      if (recRes.status === "fulfilled") {
        setRecords(recRes.value.records);
      }
      if (sumRes.status === "fulfilled") {
        setSummary(sumRes.value);
      }
    } catch (err) {
      console.error("Failed to load personal attendance", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMyData();
  }, [user]);

  // Determine if employee currently has an active check-in (open session without exit_time)
  const activeSession = records.find((r) => r.exit_time === null);

  const handleCheckIn = async () => {
    setIsSubmitting(true);
    setMessage(null);
    try {
      await attendanceApi.checkIn({ work_location: location });
      setMessage({ type: "success", text: `Checked in successfully at ${location}!` });
      fetchMyData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Check-in failed. Please check if an active session already exists.";
      setMessage({ type: "error", text: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheckOut = async () => {
    setIsSubmitting(true);
    setMessage(null);
    try {
      await attendanceApi.checkOut();
      setMessage({ type: "success", text: "Checked out successfully. Session recorded." });
      fetchMyData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Check-out failed. No active check-in found.";
      setMessage({ type: "error", text: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Employee <span className="text-gradient">Self-Service</span>
          </h1>
          <p className="page-subtitle">
            Welcome back, {user?.full_name}. Clock your working sessions and inspect telemetry.
          </p>
        </div>
      </div>

      {/* ── Clock In / Clock Out Action Card ── */}
      <div className="glass-card p-6 border-brand-500/30 relative overflow-hidden">
        <div className="absolute right-0 top-0 w-80 h-80 bg-brand-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-wrap items-center justify-between gap-6 relative">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`w-2.5 h-2.5 rounded-full animate-ping ${
                  activeSession ? "bg-emerald-400" : "bg-slate-500"
                }`}
              />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {activeSession ? "Active Attendance Session" : "Currently Off Clock"}
              </span>
            </div>

            <h2 className="text-xl font-bold text-slate-100">
              {activeSession
                ? `Clocked in at ${formatTime(activeSession.entry_time)} (${activeSession.work_location})`
                : "Ready to start your work shift?"}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Current Time:{" "}
              <span className="text-slate-200 font-mono">
                {new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST
              </span>
            </p>
          </div>

          <div className="flex items-center gap-4">
            {!activeSession ? (
              <div className="flex items-center gap-3">
                {/* Location Selector */}
                <div className="flex bg-white/5 p-1 rounded-xl border border-white/10 text-xs">
                  <button
                    type="button"
                    onClick={() => setLocation("OFFICE")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                      location === "OFFICE"
                        ? "bg-brand-600 text-white font-medium"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Briefcase className="w-3.5 h-3.5" />
                    Office
                  </button>
                  <button
                    type="button"
                    onClick={() => setLocation("WORK_FROM_HOME")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                      location === "WORK_FROM_HOME"
                        ? "bg-brand-600 text-white font-medium"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Laptop className="w-3.5 h-3.5" />
                    Remote (WFH)
                  </button>
                </div>

                <button
                  onClick={handleCheckIn}
                  disabled={isSubmitting}
                  className="btn-primary text-xs gap-1.5 shadow-glow"
                >
                  <LogIn className="w-4 h-4" />
                  {isSubmitting ? "Processing..." : "Clock In"}
                </button>
              </div>
            ) : (
              <button
                onClick={handleCheckOut}
                disabled={isSubmitting}
                className="btn-danger text-xs gap-1.5 shadow-glow"
              >
                <LogOut className="w-4 h-4" />
                {isSubmitting ? "Processing..." : "Clock Out"}
              </button>
            )}
          </div>
        </div>

        {message && (
          <div
            className={`mt-4 p-3 rounded-xl text-xs flex items-center gap-2 border animate-slide-up ${
              message.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-red-500/10 border-red-500/30 text-red-300"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            {message.text}
          </div>
        )}
      </div>

      {/* ── Summary Stats ── */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="glass-card p-4">
            <p className="text-xs text-slate-400">Total Hours</p>
            <p className="text-xl font-bold text-brand-300 mt-1 font-mono">
              {formatHours(summary.total_working_hours)}
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-xs text-slate-400">Daily Average</p>
            <p className="text-xl font-bold text-slate-100 mt-1 font-mono">
              {formatHours(summary.average_working_hours)}
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-xs text-slate-400">Office Presence</p>
            <p className="text-xl font-bold text-emerald-400 mt-1 font-mono">
              {summary.total_days_office} Days
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-xs text-slate-400">WFH Remote</p>
            <p className="text-xl font-bold text-blue-400 mt-1 font-mono">
              {summary.total_days_wfh} Days
            </p>
          </div>
        </div>
      )}

      {/* ── Personal Attendance History ── */}
      <div className="table-container">
        <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <Clock className="w-4 h-4 text-brand-400" />
            Your Check-in Log History
          </h2>
          <span className="text-xs text-slate-500">{records.length} sessions logged</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="w-6 h-6 border-2 border-brand-500/40 border-t-brand-500 rounded-full animate-spin mx-auto mb-2" />
            Loading check-in history...
          </div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No check-in history found. Clock in to start tracking!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Date</th>
                  <th className="table-header">Clock In</th>
                  <th className="table-header">Clock Out</th>
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
                      {r.exit_time ? (
                        formatTime(r.exit_time)
                      ) : (
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
  );
}
