import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CircleMinus,
  FileText,
  Loader2,
  MessageSquareText,
  Mic,
  RotateCw,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AgentTrace, Chat, PhotoWithBoxes, Stamp } from "../../components/evidence";
import { Badge, Button, ErrorNote, Meter, riskTone } from "../../components/ui";
import { api, subscribeClaim, type Claim, type ClaimFile, type Recommendation, type Signal } from "../../lib/api";
import { REC_LABEL, REC_TONE, STATUS_LABEL, clock, cx, inr, ms, shortDate, timeAgo } from "../../lib/format";

type Tab = "brief" | "coverage" | "estimate" | "fraud" | "trace" | "audit";

export default function ClaimDetail() {
  const { id = "" } = useParams();
  const [claim, setClaim] = useState<Claim | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("brief");
  const [copilot, setCopilot] = useState(false);

  useEffect(() => {
    setClaim(null);
    api.claim(id).then(setClaim).catch((e) => setError((e as Error).message));
    return subscribeClaim<Claim>(id, "adjuster", setClaim);
  }, [id]);

  if (error) return <div className="p-8"><ErrorNote>{error}</ErrorNote></div>;
  if (!claim)
    return (
      <div className="grid place-items-center py-24">
        <Loader2 className="size-6 animate-spin text-muted" />
      </div>
    );

  const ai = claim.ai;
  const working = claim.status === "queued" || claim.status === "processing";

  return (
    <div className="mx-auto max-w-7xl px-4 pb-40 pt-5 md:px-8">
      <Link to="/console" className="inline-flex items-center gap-1 text-sm font-semibold text-ink-2 hover:text-ink">
        <ArrowLeft className="size-4" /> Queue
      </Link>

      <header className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="num text-2xl font-extrabold tracking-tight">{claim.id}</h1>
            <Badge tone={claim.status === "approved" ? "go" : ["rejected", "investigating", "error"].includes(claim.status) ? "stop" : claim.status === "review" ? "ink" : "neutral"}>
              {STATUS_LABEL[claim.status]}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-ink-2">
            <span className="font-semibold text-ink">{claim.claimant.name}</span> · {claim.claimant.language_name} · {claim.claimant.phone_masked} ·{" "}
            <a href={`/api/policies/${claim.policy_number}/document`} target="_blank" className="font-semibold text-go-ink hover:underline">
              {claim.policy_number}
            </a>
          </p>
          <p className="text-sm text-muted">
            {claim.vehicle.make_model} ({claim.vehicle.year}) · <span className="num">{claim.vehicle.registration}</span> · reported {timeAgo(claim.created_at)}
            {claim.processing_seconds ? ` · AI brief in ${claim.processing_seconds.toFixed(0)} s` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          {!working && (
            <Button variant="secondary" size="sm" icon={<RotateCw className="size-3.5" />} onClick={() => api.rerun(claim.id)}>
              Re-run AI
            </Button>
          )}
          {ai && (
            <Button variant="dark" size="sm" icon={<MessageSquareText className="size-3.5" />} onClick={() => setCopilot(true)}>
              Ask ClaimPilot
            </Button>
          )}
        </div>
      </header>

      {claim.status === "error" && (
        <div className="mt-4">
          <ErrorNote>{claim.error}</ErrorNote>
        </div>
      )}

      {(working || !ai) && (
        <section className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          <div className="rounded-xl border border-line bg-surface p-5">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              {working && <Loader2 className="size-5 animate-spin" />} {working ? "Agents are reviewing this claim" : "Agent trace"}
            </h2>
            <p className="mb-4 text-sm text-muted">Live from the ADK pipeline. Each step writes structured output the next one builds on.</p>
            <AgentTrace steps={claim.trace} />
          </div>
          <Evidence claim={claim} />
        </section>
      )}

      {ai && !working && (
        <>
          <RecommendationBand claim={claim} />
          <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,1fr)]">
            <Evidence claim={claim} />
            <section className="min-w-0 rounded-xl border border-line bg-surface">
              <div className="scrollbar-thin flex gap-1 overflow-x-auto border-b border-line px-3 pt-2" role="tablist">
                {(
                  [
                    ["brief", "Brief"],
                    ["coverage", "Coverage"],
                    ["estimate", "Estimate"],
                    ["fraud", `Fraud · ${ai.fraud.risk_score}`],
                    ["trace", "Agent trace"],
                    ["audit", "Audit"],
                  ] as [Tab, string][]
                ).map(([k, label]) => (
                  <button
                    key={k}
                    role="tab"
                    aria-selected={tab === k}
                    onClick={() => setTab(k)}
                    className={cx(
                      "-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold",
                      tab === k ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink",
                      k === "fraud" && ai.fraud.risk_level === "high" && "text-stop",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="p-5">
                {tab === "brief" && <BriefTab claim={claim} />}
                {tab === "coverage" && <CoverageTab claim={claim} />}
                {tab === "estimate" && <EstimateTab claim={claim} />}
                {tab === "fraud" && <FraudTab claim={claim} />}
                {tab === "trace" && <TraceTab claim={claim} />}
                {tab === "audit" && <AuditTab claim={claim} />}
              </div>
            </section>
          </div>
          <DecisionBar claim={claim} />
        </>
      )}

      {copilot && ai && (
        <div className="fixed inset-0 z-40 flex justify-end bg-ink/30" onClick={() => setCopilot(false)}>
          <aside className="flex h-full w-full max-w-md flex-col bg-paper p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="font-bold">Ask ClaimPilot</h2>
                <p className="text-xs text-muted">Answers come from this claim file and the policy wording.</p>
              </div>
              <button onClick={() => setCopilot(false)} aria-label="Close" className="rounded-lg p-1.5 hover:bg-ink/5">
                <X className="size-5" />
              </button>
            </div>
            <div className="min-h-0 flex-1">
              <Chat
                claimId={claim.id}
                audience="adjuster"
                fill
                initial={claim.chat?.adjuster ?? []}
                placeholder="Ask about evidence, clauses or numbers…"
                suggestions={[
                  "Summarise the strongest evidence for and against paying",
                  "Which clause excludes anything here?",
                  "Walk me through the payout maths",
                  "What should I verify before approving?",
                ]}
              />
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function RecommendationBand({ claim }: { claim: Claim }) {
  const ai = claim.ai!;
  const d = ai.decision;
  const tone = REC_TONE[d.recommendation];
  const color = tone === "go" ? "text-go" : tone === "stop" ? "text-stop" : "text-amber";
  return (
    <section className="mt-5 grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-[1.6fr_0.8fr_0.8fr]">
      <div className="bg-surface p-5">
        <p className="text-xs font-semibold text-muted">AI recommends</p>
        <p className={cx("mt-0.5 text-[28px] font-extrabold leading-tight tracking-tight", color)}>{REC_LABEL[d.recommendation]}</p>
        <p className="mt-1 max-w-[60ch] text-[15px] leading-snug">{d.headline}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="neutral">{d.confidence}% confidence</Badge>
          {d.fast_track_eligible && (
            <Badge tone="go">
              <Zap className="size-3" /> Fast-track eligible
            </Badge>
          )}
          {ai.fraud.document_tampering_suspected && (
            <Badge tone="stop">
              <AlertTriangle className="size-3" /> Document tampering suspected
            </Badge>
          )}
        </div>
      </div>
      <div className="bg-surface p-5">
        <p className="text-xs font-semibold text-muted">Recommended payout</p>
        <p className="num mt-0.5 text-[28px] font-extrabold tracking-tight">{inr(d.recommended_payout_inr)}</p>
        <p className="text-xs text-muted">
          claimed <span className="num">{inr(ai.estimate.vehicle_claimed_amount || ai.intake.claimed_amount_inr)}</span>
          {ai.intake.non_vehicle_items_claimed.length > 0 && ` + ${ai.intake.non_vehicle_items_claimed.length} non-vehicle item`}
        </p>
      </div>
      <div className="bg-surface p-5">
        <p className="text-xs font-semibold text-muted">Fraud risk</p>
        <p className={cx("num mt-0.5 text-[28px] font-extrabold tracking-tight", ai.fraud.risk_level === "high" ? "text-stop" : ai.fraud.risk_level === "medium" ? "text-amber" : "text-go")}>
          {ai.fraud.risk_score}
          <span className="text-base font-bold text-muted">/100</span>
        </p>
        <div className="mt-2">
          <Meter value={ai.fraud.risk_score} tone={riskTone(ai.fraud.risk_level)} />
        </div>
        <p className="mt-1 text-xs text-muted">
          {ai.fraud_signals.flags} of {ai.fraud_signals.checked} automated checks flagged
        </p>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------

function Evidence({ claim }: { claim: Claim }) {
  const ai = claim.ai;
  const viewable = claim.files.filter((f) => f.kind !== "voice");
  const voice = claim.files.find((f) => f.kind === "voice");
  const [sel, setSel] = useState<ClaimFile | undefined>(viewable[0]);
  const [boxes, setBoxes] = useState(true);
  const [active, setActive] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);

  useEffect(() => {
    if (!sel && viewable.length) setSel(viewable[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewable.length]);

  const partsFor = (f?: ClaimFile) => (ai && f?.index ? ai.damage.damaged_parts.filter((p) => p.file_index === f.index) : []);
  const photoNote = ai && sel?.index ? ai.damage.photos.find((p) => p.file_index === sel.index) : undefined;
  const docNote = ai && sel?.index ? ai.intake.documents.find((d) => d.file_index === sel.index) : undefined;
  const meta = ai?.photo_meta.find((m) => m.file_id === sel?.id);
  const parts = partsFor(sel);
  const english = ai?.intake.statement_english;
  const masked = ai?.privacy.masked_text;

  return (
    <section className="min-w-0 space-y-4">
      <div className="rounded-xl border border-line bg-surface p-3">
        {sel ? (
          sel.mime === "application/pdf" ? (
            <iframe src={sel.url} title={sel.name} className="h-[420px] w-full rounded-lg" />
          ) : (
            <PhotoWithBoxes src={sel.url} alt={sel.name} parts={parts} show={boxes && sel.kind === "photo"} active={active} onHover={setActive} className="aspect-[4/3]" />
          )
        ) : (
          <div className="grid aspect-[4/3] place-items-center rounded-lg bg-paper text-sm text-muted">No photos or documents uploaded</div>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {viewable.map((f) => (
            <button
              key={f.id}
              onClick={() => setSel(f)}
              className={cx("relative size-16 overflow-hidden rounded-lg border-2", sel?.id === f.id ? "border-ink" : "border-transparent opacity-80 hover:opacity-100")}
              title={f.name}
            >
              {f.mime.startsWith("image/") ? (
                <img src={f.url} alt={f.name} className="size-full object-cover" />
              ) : (
                <FileText className="size-full bg-paper p-4 text-muted" />
              )}
              {f.index ? <span className="num absolute bottom-0.5 left-0.5 rounded bg-black/65 px-1 text-[10px] font-bold text-white">{f.index}</span> : null}
            </button>
          ))}
          {sel?.kind === "photo" && parts.length > 0 && (
            <label className="ml-auto inline-flex items-center gap-2 text-xs font-semibold text-ink-2">
              <input type="checkbox" checked={boxes} onChange={(e) => setBoxes(e.target.checked)} className="accent-[#0B6E4F]" /> Damage boxes
            </label>
          )}
        </div>
        {sel && (
          <div className="mt-3 space-y-1.5 border-t border-line pt-3 text-[13px]">
            <p className="font-semibold">
              File {sel.index} · {sel.name}
              {meta?.taken_at && <span className="font-normal text-muted"> · taken {shortDate(meta.taken_at)} {clock(meta.taken_at)}</span>}
            </p>
            {photoNote && <p className="text-ink-2">{photoNote.notes}</p>}
            {!photoNote && docNote && <p className="text-ink-2">{docNote.summary}</p>}
            {parts.length > 0 && (
              <ul className="mt-1 space-y-1">
                {parts.map((p) => (
                  <li
                    key={p.part_code}
                    onMouseEnter={() => setActive(p.part_code)}
                    onMouseLeave={() => setActive(null)}
                    className={cx("flex gap-2 rounded-md px-2 py-1", active === p.part_code && "bg-paper")}
                  >
                    <Badge tone={p.severity === "severe" ? "stop" : p.severity === "moderate" ? "amber" : "neutral"}>{p.severity}</Badge>
                    <span>
                      <span className="font-semibold">{p.part_name}</span> – {p.action}. {p.observation}{" "}
                      <span className="num text-muted">({Math.round(p.confidence * 100)}%)</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-line bg-surface p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-bold">Claimant's account</h3>
          {ai && claim.claimant.language !== "en" && (
            <button onClick={() => setShowOriginal(!showOriginal)} className="text-xs font-semibold text-go-ink hover:underline">
              {showOriginal ? "Show English" : `Show ${ai.intake.language} (redacted)`}
            </button>
          )}
        </div>
        <p className="mt-2 whitespace-pre-line text-[14px] leading-relaxed">
          {ai ? (showOriginal || claim.claimant.language === "en" ? masked : english) : claim.statement || "—"}
        </p>
        {voice && (
          <div className="mt-3 flex items-center gap-2">
            <Mic className="size-4 text-muted" />
            <audio controls src={voice.url} className="h-8 w-full" />
          </div>
        )}
        {ai && ai.privacy.findings.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line pt-3 text-xs">
            <ShieldCheck className="size-4 text-go" />
            <span className="font-semibold">Redacted before analysis:</span>
            {ai.privacy.findings.map((f, i) => (
              <Badge key={i} tone="go">
                {f.masked_as} · {f.by}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------

function BriefTab({ claim }: { claim: Claim }) {
  const ai = claim.ai!;
  const d = ai.decision;
  const icon = (impact: string) =>
    impact === "supports" ? <ThumbsUp className="size-4 text-go" /> : impact === "against" ? <ThumbsDown className="size-4 text-stop" /> : <CircleMinus className="size-4 text-muted" />;
  return (
    <div className="space-y-6 text-[14px]">
      <div>
        <h3 className="text-sm font-bold">Why</h3>
        <ul className="mt-2 space-y-2">
          {d.rationale.map((r, i) => (
            <li key={i} className="flex gap-2.5">
              <span className="mt-0.5">{icon(r.impact)}</span>
              <span className="leading-snug">
                {r.point} <span className="text-xs font-semibold text-muted">· {r.source}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="text-sm font-bold">Incident</h3>
        <p className="mt-1 leading-relaxed text-ink-2">{ai.intake.incident_summary}</p>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[13px]">
          <dt className="text-muted">When</dt>
          <dd>
            {shortDate(ai.intake.incident_date)} {ai.intake.incident_time !== "unknown" && ai.intake.incident_time}
          </dd>
          <dt className="text-muted">Where</dt>
          <dd>{ai.intake.incident_location}</dd>
          <dt className="text-muted">Type</dt>
          <dd className="capitalize">{ai.intake.incident_type}</dd>
          <dt className="text-muted">Damage matches story</dt>
          <dd className={ai.damage.consistent_with_statement ? "text-go" : "font-semibold text-stop"}>{ai.damage.consistent_with_statement ? "Yes" : "No"}</dd>
        </dl>
        {!ai.damage.consistent_with_statement && <p className="mt-2 rounded-lg bg-stop-tint px-3 py-2 text-[13px] text-stop-ink">{ai.damage.consistency_notes}</p>}
      </div>
      {d.next_steps.length > 0 && (
        <div>
          <h3 className="text-sm font-bold">Suggested next steps</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-ink-2">
            {d.next_steps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </div>
      )}
      {ai.intake.missing_information.length > 0 && (
        <div>
          <h3 className="text-sm font-bold">Still missing</h3>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-2">
            {ai.intake.missing_information.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <h3 className="text-sm font-bold">Draft reply to the customer ({d.customer_language})</h3>
        <p className="mt-1 rounded-lg bg-paper px-3 py-2.5 leading-relaxed">{d.customer_message_local}</p>
        {d.customer_message_local !== d.customer_message_english && <p className="mt-2 text-[13px] leading-relaxed text-muted">{d.customer_message_english}</p>}
      </div>
    </div>
  );
}

function CoverageTab({ claim }: { claim: Claim }) {
  const c = claim.ai!.coverage;
  return (
    <div className="space-y-5 text-[14px]">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={c.verdict === "covered" ? "go" : c.verdict === "not_covered" ? "stop" : "amber"}>{c.verdict.replace("_", " ")}</Badge>
        <Badge tone={c.policy_active_on_incident_date ? "go" : "stop"}>{c.policy_active_on_incident_date ? "Policy in force on incident date" : "Outside policy period"}</Badge>
        <Badge tone="neutral">Deductible {inr(c.compulsory_deductible_inr)}</Badge>
        <Badge tone="neutral">{c.depreciation_applies ? "Depreciation applies" : "Zero-Dep: no depreciation"}</Badge>
      </div>
      <p className="leading-relaxed text-ink-2">{c.summary}</p>
      <ul className="divide-y divide-line border-y border-line">
        {c.items.map((i) => (
          <li key={i.item} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <p className="font-semibold">{i.item}</p>
              <Badge tone={i.status === "covered" ? "go" : i.status === "excluded" ? "stop" : "amber"}>{i.status}</Badge>
            </div>
            <p className="mt-0.5 text-[13px] text-ink-2">{i.reason}</p>
            <blockquote className="mt-2 border-l-2 border-go pl-3 text-[13px] text-ink-2">
              <span className="font-semibold text-ink">{i.clause_ref}</span> – “{i.clause_quote}”
            </blockquote>
          </li>
        ))}
      </ul>
      {c.conditions_to_verify.length > 0 && (
        <div>
          <h3 className="text-sm font-bold">Verify before paying</h3>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-2">
            {c.conditions_to_verify.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      <a href={`/api/policies/${claim.policy_number}/document`} target="_blank" className="inline-flex items-center gap-1.5 text-sm font-semibold text-go-ink hover:underline">
        <FileText className="size-4" /> Open policy schedule and wording (PDF)
      </a>
    </div>
  );
}

function EstimateTab({ claim }: { claim: Claim }) {
  const ai = claim.ai!;
  const e = ai.estimate;
  const bills = ai.intake.bills;
  return (
    <div className="space-y-5 text-[14px]">
      <div className="overflow-x-auto">
        <table className="num w-full min-w-[460px] text-left text-[13px]">
          <thead className="border-b border-line text-xs text-muted">
            <tr>
              <th className="py-2 pr-2 font-semibold">Part</th>
              <th className="py-2 pr-2 font-semibold">Work</th>
              <th className="py-2 pr-2 text-right font-semibold">Cost</th>
              <th className="py-2 pr-2 text-right font-semibold">Depreciation</th>
              <th className="py-2 text-right font-semibold">Payable</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {e.lines.map((l) => (
              <tr key={l.part_code} className={cx(l.excluded && "text-muted line-through")}>
                <td className="py-2 pr-2">
                  {l.part_name}
                  <span className="block text-[11px] text-muted">{l.material}</span>
                </td>
                <td className="py-2 pr-2 capitalize">{l.action}</td>
                <td className="py-2 pr-2 text-right">{inr(l.gross)}</td>
                <td className="py-2 pr-2 text-right">
                  {l.depreciation_amount ? `− ${inr(l.depreciation_amount)}` : "—"}
                  {l.depreciation_pct ? <span className="block text-[11px] text-muted">{l.depreciation_pct}% on part</span> : null}
                </td>
                <td className="py-2 text-right font-semibold">{inr(l.payable)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="num ml-auto max-w-xs space-y-1 text-[13px]">
        <div className="flex justify-between"><dt className="text-ink-2">Repair cost (incl. 18% GST)</dt><dd>{inr(e.gross_total)}</dd></div>
        <div className="flex justify-between"><dt className="text-ink-2">Depreciation{e.zero_dep ? " (Zero-Dep)" : ""}</dt><dd>− {inr(e.depreciation_total)}</dd></div>
        {e.excluded_total > 0 && <div className="flex justify-between"><dt className="text-ink-2">Excluded</dt><dd>− {inr(e.excluded_total)}</dd></div>}
        <div className="flex justify-between"><dt className="text-ink-2">Compulsory deductible</dt><dd>− {inr(e.deductible)}</dd></div>
        <div className="flex justify-between border-t border-line pt-1 text-[15px] font-bold"><dt>Assessed payable</dt><dd>{inr(e.assessed_payable)}</dd></div>
        {e.capped_by_bill && <p className="text-xs text-muted">Capped at the billed amount less deductible.</p>}
        {e.not_payable_reason && <p className="text-xs font-semibold text-stop">{e.not_payable_reason}</p>}
      </dl>
      {bills.length > 0 && (
        <div>
          <h3 className="text-sm font-bold">Bills read by the intake agent</h3>
          <ul className="mt-2 space-y-2">
            {bills.map((b) => (
              <li key={b.bill_number + b.file_index} className="rounded-lg bg-paper px-3 py-2 text-[13px]">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="font-semibold">
                    {b.vendor} · {b.kind} {b.bill_number}
                  </span>
                  <span className="num font-semibold">{inr(b.total)}</span>
                </div>
                <p className="text-muted">
                  {shortDate(b.bill_date)} · {b.line_items.length} lines · {b.for_vehicle ? "vehicle repair" : "not a vehicle repair"}
                </p>
              </li>
            ))}
          </ul>
          {e.bill_vs_estimate_variance_pct !== null && (
            <p className={cx("mt-2 text-[13px]", Math.abs(e.bill_vs_estimate_variance_pct) > 25 ? "font-semibold text-stop" : "text-ink-2")}>
              Vehicle bills are {Math.abs(e.bill_vs_estimate_variance_pct)}% {e.bill_vs_estimate_variance_pct >= 0 ? "above" : "below"} ClaimPilot's estimate for the visible damage.
            </p>
          )}
        </div>
      )}
      <p className="text-xs leading-relaxed text-muted">
        Computed in code, not by the model: catalogue prices for a {e.segment}, vehicle age {Math.floor(e.vehicle_age_months / 12)} y {e.vehicle_age_months % 12} m,
        IRDAI depreciation schedule (Sec I.2) and compulsory deductible (Sec I.3).
      </p>
    </div>
  );
}

function SignalRow({ s, claim }: { s: Signal; claim: Claim }) {
  const flag = s.status === "flag";
  const dup = s.code === "duplicate_photo" && flag ? s.data : null;
  const thisPhoto = dup ? claim.files.find((f) => f.id === dup.file_id) : null;
  return (
    <li className="py-2.5">
      <div className="flex gap-2.5">
        {flag ? (
          <AlertTriangle className={cx("mt-0.5 size-4 shrink-0", s.severity === "high" ? "text-stop" : "text-amber")} />
        ) : s.status === "pass" ? (
          <Check className="mt-0.5 size-4 shrink-0 text-go" />
        ) : (
          <CircleMinus className="mt-0.5 size-4 shrink-0 text-muted" />
        )}
        <div className="min-w-0">
          <p className={cx("font-semibold", flag && s.severity === "high" && "text-stop-ink")}>{s.title}</p>
          <p className="text-[13px] text-ink-2">{s.evidence}</p>
        </div>
      </div>
      {dup && thisPhoto && (
        <div className="mt-3 grid grid-cols-2 gap-2 pl-6">
          <figure>
            <img src={thisPhoto.url} alt="Photo in this claim" className="aspect-[4/3] w-full rounded-lg object-cover" />
            <figcaption className="mt-1 text-[11px] text-muted">This claim · {thisPhoto.name}</figcaption>
          </figure>
          <figure>
            <img src={`/api/past-claims/${dup.past_claim_id}/photos/${dup.past_photo_id}`} alt="Photo from earlier claim" className="aspect-[4/3] w-full rounded-lg object-cover" />
            <figcaption className="mt-1 text-[11px] text-muted">
              {dup.past_claim_id} · {dup.past_claimant} · {shortDate(dup.past_date)}
            </figcaption>
          </figure>
          <p className="num col-span-2 text-[13px] font-semibold text-stop">{Math.round(dup.similarity * 100)}% perceptual match</p>
        </div>
      )}
    </li>
  );
}

function FraudTab({ claim }: { claim: Claim }) {
  const ai = claim.ai!;
  const f = ai.fraud;
  const signals = ai.fraud_signals.signals;
  const order = (s: Signal) => (s.status === "flag" ? 0 : s.status === "info" ? 2 : 1);
  return (
    <div className="space-y-5 text-[14px]">
      <p className="leading-relaxed text-ink-2">{f.summary}</p>
      {f.red_flags.length > 0 && (
        <div>
          <h3 className="text-sm font-bold">Red flags found by the analyst</h3>
          <ul className="mt-2 space-y-2">
            {f.red_flags.map((r, i) => (
              <li key={i} className="rounded-lg border border-line px-3 py-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-semibold">{r.title}</p>
                  <Badge tone={r.severity === "high" ? "stop" : r.severity === "medium" ? "amber" : "neutral"}>{r.severity}</Badge>
                </div>
                <p className="mt-0.5 text-[13px] text-ink-2">{r.evidence}</p>
                <p className="mt-0.5 text-[11px] font-semibold text-muted">{r.source.replace("_", " ")}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <h3 className="text-sm font-bold">
          Automated checks <span className="font-normal text-muted">· deterministic tools, rule score {ai.fraud_signals.rule_score}</span>
        </h3>
        <ul className="mt-1 divide-y divide-line">
          {[...signals].sort((a, b) => order(a) - order(b)).map((s) => (
            <SignalRow key={s.code} s={s} claim={claim} />
          ))}
        </ul>
      </div>
      {f.recommended_checks.length > 0 && (
        <div>
          <h3 className="text-sm font-bold">Recommended checks</h3>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-2">
            {f.recommended_checks.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function TraceTab({ claim }: { claim: Claim }) {
  return (
    <div className="space-y-4">
      <AgentTrace steps={claim.trace} />
      {claim.model && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 border-t border-line pt-3 text-[13px]">
          <dt className="text-muted">Engine</dt>
          <dd>{claim.model.engine}</dd>
          <dt className="text-muted">Agents model</dt>
          <dd>{claim.model.model}</dd>
          <dt className="text-muted">Adjudicator</dt>
          <dd>{claim.model.adjudicator}</dd>
          <dt className="text-muted">Privacy model</dt>
          <dd>{claim.model.gemma ?? "rules only"}</dd>
          <dt className="text-muted">Orchestration</dt>
          <dd>Google ADK · SequentialAgent → ParallelAgent → custom agents</dd>
          <dt className="text-muted">Total</dt>
          <dd className="num">{claim.processing_seconds ? ms(claim.processing_seconds * 1000) : "—"}</dd>
        </dl>
      )}
    </div>
  );
}

function AuditTab({ claim }: { claim: Claim }) {
  return (
    <ol className="space-y-3 border-l-2 border-line pl-4 text-[13px]">
      {[...claim.audit].reverse().map((a, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[21px] top-1 size-2.5 rounded-full bg-ink" />
          <p>
            <span className="font-semibold">{a.actor}</span> · {a.action.replace("_", " ")}
          </p>
          <p className="text-ink-2">{a.detail}</p>
          <p className="text-[11px] text-muted">
            {shortDate(a.at)} {clock(a.at)}
          </p>
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------------------

function DecisionBar({ claim }: { claim: Claim }) {
  const ai = claim.ai!;
  const d = ai.decision;
  const fd = claim.final_decision;
  const [amount, setAmount] = useState(String(Math.round(d.recommended_payout_inr || ai.estimate.assessed_payable || 0)));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<Recommendation | "">("");
  const [error, setError] = useState("");
  const [justDecided, setJustDecided] = useState(false);

  const amt = Number(amount.replace(/[^\d.]/g, "")) || 0;
  const approveAction: Recommendation = d.recommendation === "approve_partial" ? "approve_partial" : "approve";
  const isOverride = useMemo(
    () => (a: Recommendation) => {
      const fam = (x: Recommendation) => (x.startsWith("approve") ? "approve" : x);
      if (fam(a) !== fam(d.recommendation)) return true;
      return a.startsWith("approve") && Math.abs(amt - d.recommended_payout_inr) > Math.max(1, d.recommended_payout_inr * 0.01);
    },
    [amt, d.recommendation, d.recommended_payout_inr],
  );

  const decide = async (action: Recommendation) => {
    setError("");
    setBusy(action);
    try {
      await api.decide(claim.id, { action, amount: action.startsWith("approve") ? amt : 0, note, adjuster: "Meera Iyer (Senior adjuster)" });
      setJustDecided(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  };

  if (fd) {
    return (
      <section className="mt-6 flex flex-wrap items-center gap-6 rounded-xl border border-line bg-surface p-5">
        <Stamp action={fd.action} amount={fd.action.startsWith("approve") ? fd.amount : undefined} by={fd.by.split(" (")[0]} at={fd.at} animate={justDecided} />
        <div className="min-w-0 flex-1 text-[14px]">
          <p className="font-semibold">
            {fd.override ? `Adjuster overrode the AI (${REC_LABEL[fd.ai_recommendation]} ${inr(fd.ai_amount)})` : "Adjuster agreed with the AI recommendation"}
          </p>
          {fd.note && <p className="text-ink-2">Note: {fd.note}</p>}
          {fd.customer_message ? (
            <p className="mt-2 rounded-lg bg-paper px-3 py-2 text-[13px] text-ink-2">
              <span className="font-semibold text-ink">Sent to customer:</span> {fd.customer_message.local}
            </p>
          ) : (
            <p className="mt-2 inline-flex items-center gap-1.5 text-[13px] text-muted">
              <Loader2 className="size-3.5 animate-spin" /> Writing the customer update in {claim.claimant.language_name}…
            </p>
          )}
        </div>
      </section>
    );
  }

  const amountChanged = d.recommendation.startsWith("approve") && isOverride(approveAction);
  return (
    <section className="sticky bottom-3 z-30 mt-6 rounded-xl border border-ink/15 bg-surface/95 p-4 shadow-[0_8px_30px_rgb(20_33_43/0.12)] backdrop-blur">
      <div className="flex flex-wrap items-end gap-3">
        <label className="w-40">
          <span className="text-xs font-semibold text-muted">Payout (₹)</span>
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            inputMode="numeric"
            className="num mt-1 h-10 w-full rounded-lg border border-line-strong px-3 text-[15px] font-semibold outline-none focus:border-go"
          />
        </label>
        <label className="min-w-[220px] flex-1">
          <span className="text-xs font-semibold text-muted">
            Note{" "}
            {amountChanged ? (
              <span className="text-stop">– required: you changed the AI's amount</span>
            ) : (
              "– required if you go against the AI, request info or reject"
            )}
          </span>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Verified with workshop by phone"
            className="mt-1 h-10 w-full rounded-lg border border-line-strong px-3 text-sm outline-none focus:border-go"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => decide(approveAction)} loading={busy === approveAction} icon={<Check className="size-4" />}>
            Approve {inr(amt)}
          </Button>
          <Button variant="secondary" onClick={() => decide("request_info")} loading={busy === "request_info"}>
            Request info
          </Button>
          <Button variant="secondary" className={d.recommendation === "investigate" ? "border-stop text-stop" : ""} onClick={() => decide("investigate")} loading={busy === "investigate"}>
            Refer to SIU
          </Button>
          <Button variant="danger" onClick={() => decide("reject")} loading={busy === "reject"}>
            Reject
          </Button>
        </div>
      </div>
      {error && <p className="mt-2 text-sm font-semibold text-stop">{error}</p>}
    </section>
  );
}
