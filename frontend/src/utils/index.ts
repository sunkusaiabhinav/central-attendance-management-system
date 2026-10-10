import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merges Tailwind classes safely (handles conditional classes + deduplication) */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format ISO date string → "Oct 10, 2026" */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });
}

/** Format ISO datetime string → "10:30 AM" */
export function formatTime(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Kolkata",
  });
}

/** Format decimal hours → "7h 30m" */
export function formatHours(hours: number | null): string {
  if (hours === null || hours === undefined) return "—";
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** Today's date in YYYY-MM-DD (IST) */
export function todayIST(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

/** Compliance status → badge variant */
export function complianceBadgeVariant(status: string) {
  switch (status) {
    case "compliant":
      return "badge-success";
    case "grace_period":
      return "badge-warning";
    case "flagged":
      return "badge-danger";
    case "absent":
      return "badge-neutral";
    default:
      return "badge-neutral";
  }
}

/** Attendance status → badge variant */
export function attendanceBadgeVariant(status: string) {
  switch (status) {
    case "present":
      return "badge-success";
    case "late":
      return "badge-warning";
    case "half_day":
      return "badge-info";
    case "absent":
      return "badge-danger";
    default:
      return "badge-neutral";
  }
}
