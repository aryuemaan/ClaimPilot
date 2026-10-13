import { Check, CircleDashed, Loader2, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type ChatMessage, type DamagedPart, type Recommendation, type TraceStep } from "../lib/api";
import { cx, inr, ms, shortDate } from "../lib/format";

// ---------------------------------------------------------------------------
// Photo with damage boxes drawn from Gemini's box_2d (0-1000, [ymin, xmin, ymax, xmax])
// ---------------------------------------------------------------------------

const SEV: Record<string, string> = {
  severe: "border-stop bg-stop/10",
  moderate: "border-amber bg-amber/10",
  minor: "border-sign bg-sign/10",
};
const SEV_CHIP: Record<string, string> = { severe: "bg-stop text-white", moderate: "bg-amber text-white", minor: "bg-sign text-ink" };

export function PhotoWithBoxes({
  src,
  alt,
  parts,
  show = true,
  active,
  onHover,
  className,
}: {
  src: string;
  alt: string;
  parts: DamagedPart[];
  show?: boolean;
  active?: string | null;
  onHover?: (code: string | null) => void;
  className?: string;
}) {
  return (
    <div className={cx("relative overflow-hidden rounded-lg bg-night", className)}>
      <img src={src} alt={alt} className="block h-full w-full object-contain" />
      {show &&
        parts.map((p, i) => {
          const [y0, x0, y1, x1] = p.box_2d.length === 4 ? p.box_2d : [0, 0, 0, 0];
          // alternate labels above/below so neighbouring boxes don't cover each other's labels
          const below = i % 2 === 1 || y0 < 40;
          if (y1 <= y0 || x1 <= x0) return null;
          const dim = active && active !== p.part_code;
          return (
            <div
              key={p.part_code + p.box_2d.join()}
              onMouseEnter={() => onHover?.(p.part_code)}
              onMouseLeave={() => onHover?.(null)}
              className={cx("absolute rounded-[3px] border-2 transition-opacity", SEV[p.severity] ?? SEV.moderate, dim && "opacity-25")}
              style={{ top: `${y0 / 10}%`, left: `${x0 / 10}%`, width: `${(x1 - x0) / 10}%`, height: `${(y1 - y0) / 10}%` }}
            >
              <span
                className={cx(
                  "absolute left-[-2px] whitespace-nowrap px-1.5 py-0.5 text-[11px] font-semibold",
                  below ? "-bottom-[22px] rounded-b-[3px]" : "-top-[22px] rounded-t-[3px]",
                  SEV_CHIP[p.severity] ?? SEV_CHIP.moderate,
                )}
              >
                {p.part_name} · {p.action}
              </span>
            </div>
          );
        })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rubber-stamp decision mark
// ---------------------------------------------------------------------------

const STAMP: Record<Recommendation, { text: string; color: string }> = {
  approve: { text: "Approved", color: "#0B6E4F" },
  approve_partial: { text: "Approved", color: "#0B6E4F" },
  reject: { text: "Rejected", color: "#C2362E" },
  investigate: { text: "Referred to SIU", color: "#C2362E" },
  request_info: { text: "Info requested", color: "#A86E00" },
};

export function Stamp({ action, amount, by, at, animate }: { action: Recommendation; amount?: number; by?: string; at?: string; animate?: boolean }) {
  const s = STAMP[action];
  return (
    <div
      className={cx("inline-block rotate-[-7deg] select-none rounded-md px-4 py-2 text-center", animate && "stamp-in")}
      style={{ color: s.color, border: `3px solid ${s.color}`, boxShadow: `inset 0 0 0 2px #fff, inset 0 0 0 4px ${s.color}`, mixBlendMode: "multiply" }}
      aria-label={`${s.text}${amount ? ` ${inr(amount)}` : ""}`}
    >
      <div className="text-[22px] font-black uppercase leading-none tracking-[0.08em]">{s.text}</div>
      {amount ? <div className="num mt-1 text-lg font-extrabold leading-none">{inr(amount)}</div> : null}
      {(by || at) && (
        <div className="mt-1 text-[10px] font-semibold uppercase tracking-wider opacity-80">
          {by} {at ? `· ${shortDate(at)}` : ""}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Agent trace
// ---------------------------------------------------------------------------

const PARALLEL = new Set(["coverage_agent", "damage_agent", "fraud_signals", "fraud_analyst"]);

function StepIcon({ status }: { status: TraceStep["status"] }) {
  if (status === "done")
    return (
      <span className="grid size-6 place-items-center rounded-full bg-go text-white">
        <Check className="size-3.5" strokeWidth={3} />
      </span>
    );
  if (status === "running")
    return (
      <span className="grid size-6 place-items-center rounded-full bg-ink text-white">
        <Loader2 className="size-3.5 animate-spin" />
      </span>
    );
  if (status === "error")
    return (
      <span className="grid size-6 place-items-center rounded-full bg-stop text-white">
        <X className="size-3.5" strokeWidth={3} />
      </span>
    );
  return (
    <span className="grid size-6 place-items-center rounded-full text-line-strong">
      <CircleDashed className="size-5" />
    </span>
  );
}

export function AgentTrace({ steps, compact }: { steps: TraceStep[]; compact?: boolean }) {
  const before = steps.filter((s) => ["privacy_guard", "intake_agent"].includes(s.id));
  const par = steps.filter((s) => PARALLEL.has(s.id));
  const after = steps.filter((s) => ["cost_estimator", "adjudicator"].includes(s.id));
  const row = (s: TraceStep) => (
    <li key={s.id} className="flex gap-3">
      <StepIcon status={s.status} />
      <div className="min-w-0 flex-1 pb-3">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className={cx("font-semibold", s.status === "pending" && "text-muted")}>{s.label}</span>
          <span className="text-xs text-muted">{s.engine}</span>
          {s.ms ? <span className="num ml-auto text-xs text-muted">{ms(s.ms)}</span> : null}
        </div>
        {!compact && s.summary ? (
          <p className={cx("mt-0.5 text-[13px] leading-snug", s.status === "error" ? "text-stop" : "text-ink-2")}>{s.summary}</p>
        ) : null}
      </div>
    </li>
  );
  return (
    <ol className="text-sm">
      {before.map(row)}
      <li className="relative mb-3 ml-[11px] border-l-2 border-dashed border-line-strong pl-4">
        <span className="mb-2 block text-[11px] font-semibold text-muted">Running in parallel</span>
        <ol>{par.map(row)}</ol>
      </li>
      {after.map(row)}
    </ol>
  );
}

// ---------------------------------------------------------------------------
// Chat with the claim copilot
// ---------------------------------------------------------------------------

export function Chat({
  claimId,
  audience,
  initial,
  suggestions,
  placeholder,
  sendLabel = "Send",
  disabled,
  fill,
}: {
  claimId: string;
  audience: "adjuster" | "customer";
  initial: ChatMessage[];
  suggestions: string[];
  placeholder: string;
  sendLabel?: string;
  disabled?: boolean;
  fill?: boolean;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(initial);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initial.length > messages.length) setMessages(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial.length]);
  useEffect(() => endRef.current?.scrollIntoView({ block: "nearest" }), [messages.length, busy]);

  const ask = async (q: string) => {
    if (!q.trim() || busy) return;
    setError("");
    setBusy(true);
    setText("");
    setMessages((m) => [...m, { role: "user", text: q, at: new Date().toISOString() }]);
    try {
      const { answer } = await api.ask(claimId, q, audience);
      setMessages((m) => [...m, { role: "assistant", text: answer, at: new Date().toISOString() }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={cx("flex flex-col", fill && "h-full")}>
      <div className={cx("scrollbar-thin space-y-3 overflow-y-auto pb-2", fill ? "flex-1" : "max-h-[380px]")}>
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                disabled={disabled}
                onClick={() => ask(s)}
                className="rounded-full border border-line-strong bg-surface px-3 py-1.5 text-left text-[13px] text-ink-2 hover:border-go hover:text-go-ink disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div
              className={cx(
                "max-w-[88%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-[14px] leading-relaxed",
                m.role === "user" ? "rounded-br-sm bg-ink text-white" : "rounded-bl-sm border border-line bg-surface text-ink",
              )}
            >
              {m.text}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="size-4 animate-spin" /> Looking through the claim file…
          </div>
        )}
        {error && <p className="text-sm text-stop">{error}</p>}
        <div ref={endRef} />
      </div>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          ask(text);
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          className="h-10 min-w-0 flex-1 rounded-lg border border-line-strong bg-surface px-3 text-sm outline-none placeholder:text-muted focus:border-go"
        />
        <button
          type="submit"
          disabled={disabled || busy || !text.trim()}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-ink px-3 text-sm font-semibold text-white disabled:opacity-40"
        >
          <Send className="size-4" />
          <span className="sr-only sm:not-sr-only">{sendLabel}</span>
        </button>
      </form>
    </div>
  );
}
