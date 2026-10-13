import { BarChart3, Inbox, Play, RotateCcw, Smartphone } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useHealth } from "../../App";
import ModeNotice from "../../components/ModeNotice";
import { Brand } from "../../components/ui";
import { api } from "../../lib/api";
import { cx } from "../../lib/format";

export default function ConsoleLayout() {
  const health = useHealth();
  const [busy, setBusy] = useState<"" | "load" | "reset">("");

  const nav = ({ isActive }: { isActive: boolean }) =>
    cx("flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-semibold", isActive ? "bg-ink text-white" : "text-ink-2 hover:bg-ink/5");

  return (
    <div className="flex min-h-dvh flex-col">
      <ModeNotice />
      <div className="flex flex-1">
        <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-line bg-surface px-3 py-4 md:flex">
          <Link to="/" className="px-2">
            <Brand />
          </Link>
          <p className="mt-1 px-2 text-xs text-muted">Claims console · Suraksha General</p>
          <nav className="mt-6 space-y-1">
            <NavLink to="/console" end className={nav}>
              <Inbox className="size-4" /> Claims queue
            </NavLink>
            <NavLink to="/console/insights" className={nav}>
              <BarChart3 className="size-4" /> Insights
            </NavLink>
            <Link to="/claim" target="_blank" className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-semibold text-ink-2 hover:bg-ink/5">
              <Smartphone className="size-4" /> Customer app
            </Link>
          </nav>

          <div className="mt-auto space-y-3">
            <div className="rounded-lg bg-paper p-3">
              <p className="text-xs font-semibold text-ink">Demo controls</p>
              <button
                disabled={!!busy}
                onClick={async () => {
                  setBusy("load");
                  await api.processSamples().catch(() => {});
                  setTimeout(() => setBusy(""), 1500);
                }}
                className="mt-2 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] font-semibold text-ink-2 hover:bg-ink/5 disabled:opacity-50"
              >
                <Play className="size-3.5" /> Load the 3 sample claims
              </button>
              <button
                disabled={!!busy}
                onClick={async () => {
                  if (!confirm("Delete all claims and regenerate demo data with today's dates?")) return;
                  setBusy("reset");
                  await api.resetDemo(false).catch(() => {});
                  setBusy("");
                  window.location.assign("/console");
                }}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] font-semibold text-ink-2 hover:bg-ink/5 disabled:opacity-50"
              >
                <RotateCcw className="size-3.5" /> {busy === "reset" ? "Resetting…" : "Reset demo data"}
              </button>
            </div>
            <dl className="space-y-1 px-2 text-[11px] leading-snug text-muted">
              <div>
                <dt className="inline font-semibold">Engine: </dt>
                <dd className="inline">{health?.backend ?? "…"}</dd>
              </div>
              {health?.model && (
                <div>
                  <dt className="inline font-semibold">Model: </dt>
                  <dd className="inline">{health.model}</dd>
                </div>
              )}
              {health?.gemma_model && (
                <div>
                  <dt className="inline font-semibold">Privacy: </dt>
                  <dd className="inline">{health.gemma_model}</dd>
                </div>
              )}
              <div>
                <dt className="inline font-semibold">Storage: </dt>
                <dd className="inline">{health ? `${health.storage.documents}, ${health.storage.files}` : "…"}</dd>
              </div>
            </dl>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between border-b border-line bg-surface px-4 py-3 md:hidden">
            <Brand />
            <div className="flex gap-1 text-sm font-semibold">
              <NavLink to="/console" end className={nav}>Queue</NavLink>
              <NavLink to="/console/insights" className={nav}>Insights</NavLink>
            </div>
          </div>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
