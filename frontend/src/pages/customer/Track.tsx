import { Check, CircleDashed, Copy, Loader2, MessageCircle, RotateCw, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CustomerShell, { LangProvider } from "../../components/CustomerShell";
import { Chat } from "../../components/evidence";
import { Badge, Button, ErrorNote } from "../../components/ui";
import { api, subscribeClaim, type PublicClaim } from "../../lib/api";
import { clock, cx, inr, shortDate } from "../../lib/format";
import { asLang, fill, useLang } from "../../lib/i18n";

export default function Track() {
  return (
    <LangProvider>
      <CustomerShell>
        <TrackView />
      </CustomerShell>
    </LangProvider>
  );
}

export function TrackLookup() {
  return (
    <LangProvider>
      <CustomerShell>
        <Lookup />
      </CustomerShell>
    </LangProvider>
  );
}

function Lookup() {
  const { t } = useLang();
  const nav = useNavigate();
  const [id, setId] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (id.trim()) nav(`/track/${id.trim().toUpperCase()}`);
      }}
    >
      <h1 className="text-2xl font-extrabold">{t.trackAnother}</h1>
      <input
        value={id}
        onChange={(e) => setId(e.target.value)}
        placeholder={t.enterClaimNumber}
        className="mt-4 h-12 w-full rounded-xl border border-line-strong bg-surface px-4 outline-none focus:border-go"
      />
      <Button type="submit" size="lg" className="mt-3 w-full">
        {t.track}
      </Button>
    </form>
  );
}

const SUGGESTIONS: Record<string, string[]> = {
  en: ["Why is the amount less than my bill?", "What happens next?", "Is my phone covered?"],
  hi: ["राशि मेरे बिल से कम क्यों है?", "आगे क्या होगा?", "क्या मेरा फ़ोन कवर है?"],
  te: ["నా బిల్లు కంటే మొత్తం ఎందుకు తక్కువ?", "తర్వాత ఏం జరుగుతుంది?", "నా ఫోన్ కవర్ అవుతుందా?"],
};

function TrackView() {
  const { id = "" } = useParams();
  const { t, lang, setLang } = useLang();
  const [claim, setClaim] = useState<PublicClaim | null>(null);
  const [error, setError] = useState("");
  const [english, setEnglish] = useState(false);
  const [copied, setCopied] = useState(false);
  const [langSet, setLangSet] = useState(false);

  useEffect(() => {
    api.publicClaim(id).then(setClaim).catch((e) => setError((e as Error).message));
    return subscribeClaim<PublicClaim>(id, "customer", setClaim);
  }, [id]);

  useEffect(() => {
    if (claim && !langSet) {
      setLang(asLang(claim.claimant.language));
      setLangSet(true);
    }
  }, [claim, langSet, setLang]);

  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!claim)
    return (
      <div className="grid place-items-center py-20">
        <Loader2 className="size-6 animate-spin text-muted" />
      </div>
    );

  const working = claim.status === "queued" || claim.status === "processing";
  const s = claim.summary;
  const fd = claim.final_decision;
  const statusTone = claim.status === "approved" ? "go" : claim.status === "rejected" || claim.status === "error" ? "stop" : working ? "neutral" : "amber";

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-extrabold tracking-tight">{t.trackTitle}</h1>
          <Badge tone={statusTone}>{t.status[claim.status] ?? claim.status}</Badge>
        </div>
        <button
          onClick={() => {
            navigator.clipboard?.writeText(claim.id).catch(() => {});
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="mt-1 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
        >
          {t.claimNumber}: <span className="num font-semibold text-ink">{claim.id}</span>
          {copied ? <Check className="size-3.5 text-go" /> : <Copy className="size-3.5" />}
        </button>
        <p className="text-sm text-muted">
          {claim.vehicle.make_model} · {claim.vehicle.registration}
        </p>
      </div>

      {(working || claim.status === "error") && (
        <section className="rounded-2xl border border-line bg-surface p-5">
          {claim.status === "error" ? (
            <>
              <h2 className="text-lg font-bold text-stop">{t.stopped}</h2>
              <p className="mt-1 text-sm text-ink-2">{claim.error}</p>
              <Button className="mt-4" variant="secondary" icon={<RotateCw className="size-4" />} onClick={() => api.rerun(claim.id)}>
                {t.tryAgain}
              </Button>
            </>
          ) : (
            <>
              <h2 className="text-lg font-bold">{t.working}</h2>
              <p className="mt-1 text-sm text-ink-2">{t.workingHint}</p>
              <div className="relative mt-4 h-1 overflow-hidden rounded-full bg-ink/10">
                <span className="bar-indeterminate absolute inset-y-0 w-1/3 rounded-full bg-go" />
              </div>
            </>
          )}
          <ol className="mt-5 space-y-3">
            {claim.progress.map((p) => (
              <li key={p.label} className="flex items-center gap-3 text-[15px]">
                {p.status === "done" ? (
                  <span className="grid size-6 place-items-center rounded-full bg-go text-white">
                    <Check className="size-3.5" strokeWidth={3} />
                  </span>
                ) : p.status === "running" ? (
                  <Loader2 className="size-6 animate-spin text-ink" />
                ) : p.status === "error" ? (
                  <span className="grid size-6 place-items-center rounded-full bg-stop text-white">
                    <X className="size-3.5" />
                  </span>
                ) : (
                  <CircleDashed className="size-6 text-line-strong" />
                )}
                <span className={cx(p.status === "pending" && "text-muted", p.status === "running" && "font-semibold")}>
                  {t.progress[p.label] ?? p.label}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {fd && fd.customer_message && (
        <section
          className={cx(
            "rounded-2xl p-5",
            fd.action.startsWith("approve") ? "bg-go text-white" : fd.action === "request_info" ? "bg-amber-tint" : "bg-surface border border-line",
          )}
        >
          {fd.action.startsWith("approve") && <p className="num text-3xl font-extrabold">{fill(t.approvedFor, { amount: inr(fd.amount) })}</p>}
          <p className={cx("text-[15px] leading-relaxed", fd.action.startsWith("approve") && "mt-2 text-white/90")}>
            {english || lang === "en" ? fd.customer_message.english : fd.customer_message.local}
          </p>
        </section>
      )}

      {s && (
        <section className="rounded-2xl border border-line bg-surface p-5">
          <div className="flex items-start gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-full bg-go-tint">
              <MessageCircle className="size-5 text-go" />
            </span>
            <div className="min-w-0">
              <p className="whitespace-pre-line text-[15px] leading-relaxed">{english ? s.message_english : s.message_local}</p>
              {s.message_local !== s.message_english && (
                <button onClick={() => setEnglish(!english)} className="mt-2 text-sm font-semibold text-go-ink hover:underline">
                  {english ? t.showOriginal : t.showEnglish}
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {s?.estimate && !fd && (
        <section className="rounded-2xl border border-line bg-surface p-5">
          <p className="text-sm font-semibold text-muted">{t.estimated}</p>
          <p className="num mt-1 text-4xl font-extrabold tracking-tight">{inr(s.estimate.recommended_payout)}</p>
          <p className="text-[13px] text-muted">{t.subjectToApproval}</p>
          <dl className="num mt-4 space-y-1.5 border-t border-line pt-3 text-sm">
            <Row label={t.repairCost} value={inr(s.estimate.gross_total)} />
            <Row label={t.depreciation} value={`− ${inr(s.estimate.depreciation_total)}`} />
            <Row label={t.deductible} value={`− ${inr(s.estimate.deductible)}`} />
            <Row label={t.payable} value={inr(s.estimate.recommended_payout)} strong />
          </dl>
        </section>
      )}

      {s && s.coverage.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-muted">{t.whatsCovered}</h2>
          <ul className="mt-2 divide-y divide-line rounded-2xl border border-line bg-surface">
            {s.coverage.map((c) => (
              <li key={c.item} className="flex items-start gap-3 px-4 py-3">
                <Badge tone={c.status === "covered" ? "go" : c.status === "excluded" ? "stop" : "amber"} className="mt-0.5">
                  {c.status === "covered" ? t.covered : c.status === "excluded" ? t.excluded : t.limited}
                </Badge>
                <div className="min-w-0">
                  <p className="text-[15px] font-semibold">{c.item}</p>
                  <p className="text-[13px] text-muted">
                    {c.reason} <span className="whitespace-nowrap">({c.clause_ref})</span>
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!working && claim.status !== "error" && (
        <section>
          <h2 className="text-sm font-semibold text-muted">{t.askTitle}</h2>
          <div className="mt-2 rounded-2xl border border-line bg-surface p-3">
            <Chat
              claimId={claim.id}
              audience="customer"
              initial={claim.chat}
              suggestions={SUGGESTIONS[lang] ?? SUGGESTIONS.en}
              placeholder={t.askPlaceholder}
              sendLabel={t.send}
            />
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm font-semibold text-muted">{t.timeline}</h2>
        <ol className="mt-2 space-y-3 border-l-2 border-line pl-4">
          {[...claim.timeline].reverse().map((e, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[21px] top-1.5 size-2.5 rounded-full bg-go" />
              <p className="text-[15px] leading-snug">{t.timelineKinds[e.kind] ?? (lang === "en" && e.text_english ? e.text_english : e.text)}</p>
              <p className="text-xs text-muted">
                {shortDate(e.at)} · {clock(e.at)}
              </p>
            </li>
          ))}
        </ol>
      </section>

      <div className="flex flex-wrap gap-4 border-t border-line pt-5 text-sm font-semibold">
        <Link to="/claim" className="text-go-ink hover:underline">{t.newClaim}</Link>
        <Link to="/track" className="text-go-ink hover:underline">{t.trackAnother}</Link>
      </div>
    </div>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={cx("flex justify-between", strong && "border-t border-line pt-1.5 font-bold")}>
      <dt className={strong ? "" : "text-ink-2"}>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
