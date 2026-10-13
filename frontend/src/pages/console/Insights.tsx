import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Insights as Data } from "../../lib/api";
import { REC_LABEL, cx, inr } from "../../lib/format";

function Bars({ data, colors }: { data: [string, number][]; colors: Record<string, string> }) {
  const max = Math.max(1, ...data.map(([, v]) => v));
  return (
    <ul className="space-y-2.5">
      {data.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[8rem_1fr_2.5rem] items-center gap-3 text-sm">
          <span className="truncate text-ink-2">{k}</span>
          <span className="h-3 overflow-hidden rounded-full bg-ink/[0.06]">
            <span className={cx("block h-full rounded-full", colors[k] ?? "bg-ink-2")} style={{ width: `${(v / max) * 100}%` }} />
          </span>
          <span className="num text-right font-semibold">{v}</span>
        </li>
      ))}
    </ul>
  );
}

export default function Insights() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => {
    const load = () => api.insights().then(setD).catch(() => {});
    load();
    const id = setInterval(() => document.visibilityState === "visible" && load(), 6000);
    return () => clearInterval(id);
  }, []);

  if (!d)
    return (
      <div className="grid place-items-center py-24">
        <Loader2 className="size-6 animate-spin text-muted" />
      </div>
    );

  const nowMin = d.avg_ai_seconds !== null ? d.avg_ai_seconds / 60 + (d.avg_minutes_to_decide ?? 0) : null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
      <h1 className="text-2xl font-extrabold tracking-tight">Insights</h1>
      <p className="text-sm text-muted">How the AI desk is performing, and how often adjusters agree with it.</p>

      <section className="mt-6 rounded-xl border border-line bg-surface p-6">
        <h2 className="text-sm font-bold">Time from report to decision</h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <div>
            <p className="text-xs font-semibold text-muted">Before ClaimPilot</p>
            <p className="num text-[44px] font-extrabold leading-none tracking-tight text-ink-2">
              {d.baseline.avg_days_to_settle ?? "—"}
              <span className="ml-1 text-xl font-bold">days</span>
            </p>
            <p className="mt-1 text-xs text-muted">Average over {d.baseline.past_claims} past claims · seeded demo history</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-muted">With ClaimPilot</p>
            <p className="num text-[44px] font-extrabold leading-none tracking-tight text-go">
              {nowMin !== null ? (nowMin < 60 ? nowMin.toFixed(1) : (nowMin / 60).toFixed(1)) : "—"}
              <span className="ml-1 text-xl font-bold">{nowMin !== null && nowMin >= 60 ? "hours" : "minutes"}</span>
            </p>
            <p className="mt-1 text-xs text-muted">
              AI brief in {d.avg_ai_seconds ?? "—"} s on average, plus the adjuster's time to decide
            </p>
          </div>
        </div>
      </section>

      <dl className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-4">
        {[
          ["Claims analysed", String(d.analysed), `${d.awaiting_decision} awaiting a decision`],
          ["Adjuster agreed with AI", d.agreement_rate !== null ? `${d.agreement_rate}%` : "—", `${d.decided} decided`],
          ["Fast-track eligible", String(d.fast_track), "low risk, under ₹50,000"],
          ["Held for investigation", inr(d.amount_held_inr), "high-risk claimed amount"],
        ].map(([k, v, h]) => (
          <div key={k} className="bg-surface px-4 py-4">
            <dt className="text-xs font-semibold text-muted">{k}</dt>
            <dd className="num mt-0.5 text-2xl font-extrabold tracking-tight">{v}</dd>
            <dd className="text-xs text-muted">{h}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <section className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-sm font-bold">Fraud risk</h2>
          <div className="mt-4">
            <Bars
              data={[
                ["Low", d.risk.low ?? 0],
                ["Medium", d.risk.medium ?? 0],
                ["High", d.risk.high ?? 0],
              ]}
              colors={{ Low: "bg-go", Medium: "bg-amber", High: "bg-stop" }}
            />
          </div>
        </section>
        <section className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-sm font-bold">AI recommendations</h2>
          <div className="mt-4">
            <Bars
              data={Object.entries(d.recommendations).map(([k, v]) => [REC_LABEL[k as keyof typeof REC_LABEL] ?? k, v])}
              colors={{ Approve: "bg-go", "Approve in part": "bg-go/60", Investigate: "bg-stop", "Request info": "bg-amber", Reject: "bg-stop-ink" }}
            />
          </div>
          <p className="mt-4 text-xs text-muted">Approved so far: {inr(d.amount_approved_inr)}</p>
        </section>
      </div>
    </div>
  );
}
