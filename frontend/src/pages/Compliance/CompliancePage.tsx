import { useEffect, useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Play,
  Mail,
  AlertTriangle,
  Calendar,
  CheckCircle2,
} from "lucide-react";
import { complianceApi } from "@/api/compliance";
import { useAuthStore } from "@/store/authStore";
import { formatDate, formatHours } from "@/utils";
import type { ComplianceViolation, ComplianceRecord } from "@/types";

export function CompliancePage() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "ADMIN";

  const [violations, setViolations] = useState<ComplianceViolation[]>([]);
  const [myRecords, setMyRecords] = useState<ComplianceRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Evaluation action states
  const [evalWeek, setEvalWeek] = useState(getRecentMonday());
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isSendingEmails, setIsSendingEmails] = useState(false);

  function getRecentMonday() {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // adjust when day is sunday
    d.setDate(diff);
    return d.toLocaleDateString("en-CA");
  }

  const fetchData = async () => {
    setIsLoading(true);
    setActionMsg(null);
    try {
      if (isAdmin) {
        const res = await complianceApi.listViolations({ page: 1, page_size: 100 });
        setViolations(res.violations);
      } else {
        const res = await complianceApi.myCompliance();
        setMyRecords(res);
      }
    } catch (err) {
      console.error("Failed to fetch compliance", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [isAdmin]);

  const handleRunEvaluation = async () => {
    setIsEvaluating(true);
    setActionMsg(null);
    try {
      const res = await complianceApi.evaluate(evalWeek, true);
      setActionMsg({
        type: "success",
        text: `Evaluation complete! Evaluated ${res.evaluated_employees} employees (${res.compliant} compliant, ${res.non_compliant} non-compliant).`,
      });
      fetchData();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to run compliance evaluation.";
      setActionMsg({ type: "error", text: msg });
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleSendEmails = async () => {
    setIsSendingEmails(true);
    setActionMsg(null);
    try {
      const res = await complianceApi.sendWarningEmails(evalWeek, true);
      setActionMsg({
        type: "success",
        text: `Warning emails dispatched! ${res.emails_sent} sent, ${res.emails_failed} failed out of ${res.total_non_compliant} non-compliant employees.`,
      });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to dispatch warning emails.";
      setActionMsg({ type: "error", text: msg });
    } finally {
      setIsSendingEmails(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Policy & Compliance <span className="text-gradient">Engine</span>
          </h1>
          <p className="page-subtitle">
            Automated monitoring of the 3-day office, 15 weekly hours, and 5h/day average threshold
          </p>
        </div>
      </div>

      {/* ── Admin Action Bar ── */}
      {isAdmin && (
        <div className="glass-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Calendar className="w-4 h-4 text-brand-400" />
              <div>
                <p className="text-xs font-semibold text-slate-300">Target Evaluation Monday:</p>
                <input
                  type="date"
                  value={evalWeek}
                  onChange={(e) => setEvalWeek(e.target.value)}
                  className="input-field py-1.5 px-3 text-xs w-40 mt-1"
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleRunEvaluation}
                disabled={isEvaluating}
                className="btn-primary text-xs gap-1.5"
              >
                <Play className="w-3.5 h-3.5" />
                {isEvaluating ? "Evaluating..." : "Run Evaluation"}
              </button>

              <button
                onClick={handleSendEmails}
                disabled={isSendingEmails}
                className="btn-secondary text-xs gap-1.5 border-amber-500/30 text-amber-300 hover:bg-amber-500/10"
              >
                <Mail className="w-3.5 h-3.5" />
                {isSendingEmails ? "Sending..." : "Dispatch Warning Emails"}
              </button>
            </div>
          </div>

          {actionMsg && (
            <div
              className={`mt-4 p-3 rounded-xl text-xs flex items-center gap-2 border animate-slide-up ${
                actionMsg.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                  : "bg-red-500/10 border-red-500/30 text-red-300"
              }`}
            >
              {actionMsg.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              )}
              {actionMsg.text}
            </div>
          )}
        </div>
      )}

      {/* ── Main View: Admin Violation Roster or Employee Personal View ── */}
      {isAdmin ? (
        <div className="table-container">
          <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              Policy Violations ({violations.length})
            </h2>
            <span className="text-xs text-slate-500">
              Evaluated per ISO work week
            </span>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              <div className="w-6 h-6 border-2 border-brand-500/40 border-t-brand-500 rounded-full animate-spin mx-auto mb-2" />
              Analyzing compliance infractions...
            </div>
          ) : violations.length === 0 ? (
            <div className="p-12 text-center text-emerald-400 text-sm flex flex-col items-center gap-2">
              <ShieldCheck className="w-8 h-8 text-emerald-400/80" />
              <p className="font-semibold">Zero Compliance Violations Found</p>
              <p className="text-slate-500 text-xs">All active employees have fulfilled policy guidelines.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Employee</th>
                    <th className="table-header">Week Window</th>
                    <th className="table-header">Office Days</th>
                    <th className="table-header">Working Hours</th>
                    <th className="table-header">Infraction Reasons</th>
                    <th className="table-header">Evaluated At</th>
                  </tr>
                </thead>
                <tbody>
                  {violations.map((v) => (
                    <tr key={v.id} className="table-row">
                      <td className="table-cell">
                        <div>
                          <p className="font-semibold text-slate-200">{v.employee_name}</p>
                          <p className="text-xs text-slate-500">{v.employee_email}</p>
                        </div>
                      </td>
                      <td className="table-cell font-mono text-xs">
                        {v.week_start} → {v.week_end}
                      </td>
                      <td className="table-cell font-mono text-amber-400">
                        {v.attendance_days} days
                      </td>
                      <td className="table-cell font-mono text-red-400">
                        {formatHours(v.total_working_hours)}
                      </td>
                      <td className="table-cell">
                        <div className="flex flex-wrap gap-1.5">
                          {v.violation_reasons.map((r, i) => (
                            <span
                              key={i}
                              className="text-[11px] bg-red-500/10 text-red-300 border border-red-500/20 px-2 py-0.5 rounded-md"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="table-cell text-xs text-slate-500">
                        {formatDate(v.evaluated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Employee Self-View */
        <div className="table-container">
          <div className="px-6 py-4 border-b border-white/8">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-brand-400" />
              Your Weekly Compliance Records
            </h2>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              Loading your compliance telemetry...
            </div>
          ) : myRecords.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm">
              No compliance history evaluated for your profile yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Week</th>
                    <th className="table-header">Office Days</th>
                    <th className="table-header">Total Hours</th>
                    <th className="table-header">Avg Hours/Day</th>
                    <th className="table-header">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {myRecords.map((r) => (
                    <tr key={r.id} className="table-row">
                      <td className="table-cell font-mono text-xs">
                        {r.week_start} to {r.week_end}
                      </td>
                      <td className="table-cell font-mono">{r.attendance_days}</td>
                      <td className="table-cell font-mono">{formatHours(r.total_working_hours)}</td>
                      <td className="table-cell font-mono">{formatHours(r.average_working_hours)}</td>
                      <td className="table-cell">
                        {r.is_compliant ? (
                          <span className="badge-success">Compliant</span>
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
      )}
    </div>
  );
}
