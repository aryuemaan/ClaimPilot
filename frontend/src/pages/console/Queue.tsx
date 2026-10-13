import { Loader2, Play, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Meter, riskTone } from "../../components/ui";
import { api, type ClaimRow } from "../../lib/api";
import { REC_LABEL, REC_TONE, STATUS_LABEL, cx, inr, timeAgo } from "../../lib/format";

type Filter = "all" | "review" | "high" | "fast" | "decided";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "review", label: "Needs decision" },
  { id: "high", label: "High risk" },
  { id: "fast", label: "Fast-track" },
  { id: "decided", label: "Decided" },
];

export default function Queue() {
  const nav = useNavigate();
  const [rows, setRows] = useState<ClaimRow[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => api.claims().then((r) => alive && setRows(r)).catch(() => alive && setRows([]));
    load();
    // poll only while the tab is visible, to keep Firestore reads low
    const id = setInterval(() => document.visibilityState === "visible" && load(), 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const counts = useMemo(() => {
    const r = rows ?? [];
    return {
      review: r.filter((x) => x.status === "review").length,
      high: r.filter((x) => x.risk_level === "high").length,
      heldAmount: r.filter((x) => x.risk_level === "high").reduce((a, x) => a + (x.claimed_amount ?? 0), 0),
      fast: r.filter((x) => x.fast_track && x.status === "review").length,
      avg: (() => {
        const s = r.map((x) => x.processing_seconds).filter((x): x is number => !!x);
        return s.length ? s.reduce((a, b) => a + b, 0) / s.length : null;
      })(),
    };
  }, [rows]);

  const shown = (rows ?? []).filter((r) => {
    if (filter === "review") return r.status === "review";
    if (filter === "high") return r.risk_level === "high";
    if (filter === "fast") return !!r.fast_track;
    if (filter === "decided") return !!r.final_decision;
    return true;
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Claims queue</h1>
          <p className="text-sm text-muted">Every claim arrives with an AI brief. You make the call.</p>
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-2 divide-line overflow-hidden rounded-xl border border-line bg-surface md:grid-cols-4 md:divide-x">
        <Kpi label="Needs your decision" value={String(counts.review)} />
        <Kpi label="Fast-track ready" value={String(counts.fast)} hint="low risk, under ₹50,000" />
        <Kpi label="High risk held" value={inr(counts.heldAmount)} hint={`${counts.high} claim${counts.high === 1 ? "" : "s"}`} tone="stop" />
        <Kpi label="Average AI review" value={counts.avg ? `${counts.avg.toFixed(0)} s` : "—"} hint="from upload to brief" />
      </dl>

      <div className="mt-6 flex flex-wrap gap-1" role="tablist">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            role="tab"
            aria-selected={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={cx("rounded-lg px-3 py-1.5 text-sm font-semibold", filter === f.id ? "bg-ink text-white" : "text-ink-2 hover:bg-ink/5")}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-3 overflow-x-auto rounded-xl border border-line bg-surface">
        {rows === null ? (
          <div className="grid place-items-center py-16">
            <Loader2 className="size-6 animate-spin text-muted" />
          </div>
        ) : rows.length === 0 ? (
          <div className="px-6 py-14 text-center">
            <p className="text-lg font-bold">No claims yet</p>
            <p className="mx-auto mt-1 max-w-md text-sm text-muted">
              Submit one from the customer app, or load the three sample claims to see the queue fill up live.
            </p>
            <div className="mt-5 flex justify-center gap-2">
              <Button
                icon={<Play className="size-4" />}
                loading={loading}
                onClick={async () => {
                  setLoading(true);
                  await api.processSamples();
                  setTimeout(() => setLoading(false), 2000);
                }}
              >
                Load the 3 sample claims
              </Button>
              <a href="/claim" target="_blank" className="inline-flex h-10 items-center rounded-lg border border-line-strong px-4 text-sm font-semibold hover:border-ink-2">
                Open customer app
              </a>
            </div>
          </div>
        ) : (
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="border-b border-line text-xs text-muted">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Claim</th>
                <th className="px-4 py-2.5 font-semibold">Claimant</th>
                <th className="px-4 py-2.5 font-semibold">Vehicle</th>
                <th className="px-4 py-2.5 text-right font-semibold">Claimed</th>
                <th className="px-4 py-2.5 font-semibold">AI recommends</th>
                <th className="w-36 px-4 py-2.5 font-semibold">Fraud risk</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {shown.map((r) => (
                <tr key={r.id} onClick={() => nav(`/console/claims/${r.id}`)} className="cursor-pointer align-top hover:bg-paper">
                  <td className="px-4 py-3">
                    <span className="num font-semibold">{r.id}</span>
                    <span className="block text-xs text-muted">{timeAgo(r.created_at)}</span>
                  </td>
                  <td className="px-4 py-3">
                    {r.claimant}
                    <span className="block text-xs text-muted">{r.language_name}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="num">{r.vehicle.registration}</span>
                    <span className="block text-xs text-muted">{r.vehicle.make_model}</span>
                  </td>
                  <td className="num px-4 py-3 text-right">{r.claimed_amount ? inr(r.claimed_amount) : "—"}</td>
                  <td className="max-w-[320px] px-4 py-3">
                    {r.recommendation ? (
                      <>
                        <span className="flex flex-wrap items-center gap-1.5">
                          <Badge tone={REC_TONE[r.recommendation]}>{REC_LABEL[r.recommendation]}</Badge>
                          {r.recommendation.startsWith("approve") && <span className="num font-semibold">{inr(r.recommended_payout)}</span>}
                          {r.fast_track && (
                            <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-go">
                              <Zap className="size-3" /> fast-track
                            </span>
                          )}
                        </span>
                        <span className="mt-1 line-clamp-2 block text-xs text-muted">{r.headline}</span>
                      </>
                    ) : r.status === "error" ? (
                      <span className="text-xs text-stop">Analysis stopped – open to retry</span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-xs text-muted">
                        <Loader2 className="size-3.5 animate-spin" /> Agents working…
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {r.risk_score !== null && r.risk_score !== undefined ? (
                      <span className="block">
                        <span className="num flex justify-between text-xs">
                          <span className="font-semibold">{r.risk_score}</span>
                          <span className="text-muted">{r.risk_level}</span>
                        </span>
                        <span className="mt-1 block">
                          <Meter value={r.risk_score} tone={riskTone(r.risk_level)} />
                        </span>
                      </span>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      tone={
                        r.status === "approved" ? "go" : r.status === "rejected" || r.status === "investigating" || r.status === "error" ? "stop" : r.status === "review" ? "ink" : "neutral"
                      }
                    >
                      {STATUS_LABEL[r.status] ?? r.status}
                    </Badge>
                  </td>
                </tr>
              ))}
              {shown.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-sm text-muted">
                    Nothing here with this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "stop" }) {
  return (
    <div className="border-b border-line px-4 py-3.5 md:border-b-0">
      <dt className="text-xs font-semibold text-muted">{label}</dt>
      <dd className={cx("num mt-0.5 text-2xl font-extrabold tracking-tight", tone === "stop" && "text-stop")}>{value}</dd>
      {hint && <dd className="text-xs text-muted">{hint}</dd>}
    </div>
  );
}
