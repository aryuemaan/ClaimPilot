import type { Recommendation } from "./api";

/** ₹ with Indian digit grouping: 1234567 -> ₹12,34,567 */
export function inr(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const v = Math.round(n);
  return (v < 0 ? "-₹" : "₹") + Math.abs(v).toLocaleString("en-IN");
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function shortDate(iso: string | null | undefined, locale = "en-IN"): string {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
  return d.toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
}

export function clock(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}

export const REC_LABEL: Record<Recommendation, string> = {
  approve: "Approve",
  approve_partial: "Approve in part",
  investigate: "Investigate",
  request_info: "Request info",
  reject: "Reject",
};

export const REC_TONE: Record<Recommendation, "go" | "amber" | "stop" | "ink"> = {
  approve: "go",
  approve_partial: "go",
  investigate: "stop",
  request_info: "amber",
  reject: "stop",
};

export const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  processing: "AI reviewing",
  review: "Needs decision",
  approved: "Approved",
  rejected: "Rejected",
  info_requested: "Info requested",
  investigating: "With SIU",
  error: "Stopped",
};

export function ms(v: number | null | undefined): string {
  if (v === null || v === undefined) return "";
  return v < 1000 ? `${v} ms` : `${(v / 1000).toFixed(1)} s`;
}

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
