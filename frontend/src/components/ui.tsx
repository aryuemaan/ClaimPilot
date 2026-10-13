import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../lib/format";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "dark";
type Size = "sm" | "md" | "lg";

const VARIANT: Record<Variant, string> = {
  primary: "bg-go text-white hover:bg-go-ink disabled:bg-go/50",
  secondary: "bg-surface text-ink border border-line-strong hover:border-ink-2 hover:bg-paper disabled:text-muted",
  ghost: "text-ink-2 hover:bg-ink/5 disabled:text-muted",
  danger: "bg-stop text-white hover:bg-stop-ink disabled:bg-stop/50",
  dark: "bg-ink text-white hover:bg-ink-2 disabled:bg-ink/50",
};
const SIZE: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px] gap-1.5 rounded-md",
  md: "h-10 px-4 text-sm gap-2 rounded-lg",
  lg: "h-13 px-5 text-base gap-2 rounded-xl",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  icon,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; loading?: boolean; icon?: ReactNode }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={cx(
        "inline-flex select-none items-center justify-center font-semibold transition-colors",
        VARIANT[variant],
        SIZE[size],
        className,
      )}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}

type Tone = "go" | "amber" | "stop" | "ink" | "neutral";
const TONE: Record<Tone, string> = {
  go: "bg-go-tint text-go-ink",
  amber: "bg-amber-tint text-amber",
  stop: "bg-stop-tint text-stop-ink",
  ink: "bg-ink text-white",
  neutral: "bg-ink/[0.06] text-ink-2",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-semibold", TONE[tone], className)}>
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cx("size-4 animate-spin", className)} aria-hidden />;
}

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect width="64" height="64" rx="14" fill="#0B6E4F" />
      <path d="M14 40c4-11 10-17 18-17s14 6 18 17" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" />
      <circle cx="22" cy="42" r="5" fill="#F2C230" />
      <circle cx="42" cy="42" r="5" fill="#F2C230" />
      <path d="M28 18l4-6 4 6" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Brand({ className, light }: { className?: string; light?: boolean }) {
  return (
    <span className={cx("inline-flex items-center gap-2", className)}>
      <BrandMark className="size-7" />
      <span className={cx("text-[17px] font-extrabold tracking-tight", light ? "text-white" : "text-ink")}>ClaimPilot</span>
    </span>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p role="alert" className="rounded-lg border border-stop/30 bg-stop-tint px-3 py-2 text-sm text-stop-ink">
      {children}
    </p>
  );
}

export function Meter({ value, tone }: { value: number; tone: "go" | "amber" | "stop" }) {
  const color = tone === "go" ? "bg-go" : tone === "amber" ? "bg-amber" : "bg-stop";
  return (
    <span className="block h-1.5 w-full overflow-hidden rounded-full bg-ink/10" role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <span className={cx("block h-full rounded-full", color)} style={{ width: `${Math.max(3, Math.min(100, value))}%` }} />
    </span>
  );
}

export function riskTone(level?: string | null): "go" | "amber" | "stop" {
  return level === "high" ? "stop" : level === "medium" ? "amber" : "go";
}
