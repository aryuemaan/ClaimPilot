import { ArrowRight, ClipboardCheck, Smartphone } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useHealth } from "../App";
import ModeNotice from "../components/ModeNotice";
import { Brand } from "../components/ui";
import { api, type SampleKit } from "../lib/api";

/** The pipeline drawn as a road: each agent is a stop with a highway-style sign. */
function RoadMap() {
  const road = "#1d2a33";
  const sign = (x: number, y: number, w: number, title: string, sub: string, anchor: "start" | "middle" = "start") => {
    const left = anchor === "middle" ? x - w / 2 : x;
    return (
      <g>
        <rect x={left} y={y} width={w} height={44} rx={5} fill="#0B6E4F" />
        <rect x={left + 3} y={y + 3} width={w - 6} height={38} rx={3} fill="none" stroke="#fff" strokeWidth={1.4} />
        <text x={left + w / 2} y={y + 20} textAnchor="middle" fill="#fff" fontSize={13} fontWeight={700}>
          {title}
        </text>
        <text x={left + w / 2} y={y + 34} textAnchor="middle" fill="#d9efe5" fontSize={10.5}>
          {sub}
        </text>
      </g>
    );
  };
  const node = (x: number, y: number, ring: string) => <circle cx={x} cy={y} r={9} fill="#fff" stroke={ring} strokeWidth={4} />;
  const lane = (x: number) => `M220 222 C220 262 ${x} 252 ${x} 292 L${x} 404 C${x} 444 220 434 220 474`;
  return (
    <svg viewBox="0 0 440 690" className="h-auto w-full max-w-[520px]" role="img"
      aria-label="Claim journey: privacy guard, intake, then coverage, damage and fraud agents in parallel, cost estimator, adjudicator, and a human adjuster's decision">
      {/* asphalt */}
      <g fill="none" stroke={road} strokeLinecap="round">
        <path d="M220 34 L220 230" strokeWidth={26} />
        <path d={lane(80)} strokeWidth={22} />
        <path d={lane(220)} strokeWidth={22} />
        <path d={lane(360)} strokeWidth={22} />
        <path d="M220 470 L220 650" strokeWidth={26} />
      </g>
      {/* lane markings */}
      <g fill="none" stroke="#F2C230" strokeWidth={2.5} strokeDasharray="9 9">
        <path d="M220 40 L220 226" />
        <path d={lane(80)} />
        <path d={lane(220)} />
        <path d={lane(360)} />
        <path d="M220 474 L220 646" />
      </g>
      {/* start */}
      <circle cx={220} cy={34} r={15} fill="#F2C230" stroke={road} strokeWidth={3} />
      <text x={246} y={30} fontSize={13} fontWeight={700} fill="#14212b">Customer reports</text>
      <text x={246} y={46} fontSize={11.5} fill="#3a4a53">voice note · photos · bills</text>

      {node(220, 110, "#a86e00")}
      {sign(246, 88, 184, "Privacy guard", "rules + Gemma mask IDs")}
      {node(220, 186, "#0B6E4F")}
      {sign(246, 164, 184, "Intake agent", "Gemini reads everything")}

      {node(80, 300, "#0B6E4F")}
      {node(220, 300, "#0B6E4F")}
      {node(360, 300, "#0B6E4F")}
      {sign(80, 322, 124, "Coverage", "policy PDF · clauses", "middle")}
      {sign(220, 322, 124, "Damage", "vision · parts · boxes", "middle")}
      {sign(360, 322, 124, "Fraud", "8 checks · forensics", "middle")}
      <text x={150} y={400} textAnchor="middle" fontSize={11} fontWeight={600} fill="#66767e">in parallel</text>

      {node(220, 512, "#3a4a53")}
      {sign(246, 490, 184, "Cost estimator", "parts · labour · depreciation")}
      {node(220, 586, "#0B6E4F")}
      {sign(246, 564, 184, "Adjudicator", "brief + reply in their language")}

      {/* finish: the human signs */}
      <g transform="translate(220 652) rotate(-7)">
        <rect x={-58} y={-18} width={116} height={36} rx={4} fill="#fff" stroke="#0B6E4F" strokeWidth={3} />
        <text x={0} y={6} textAnchor="middle" fontSize={14} fontWeight={900} fill="#0B6E4F" letterSpacing="1.5">
          APPROVED
        </text>
      </g>
      <text x={290} y={648} fontSize={13} fontWeight={700} fill="#14212b">Adjuster decides</text>
      <text x={290} y={664} fontSize={11.5} fill="#3a4a53">one click, with the full brief</text>
    </svg>
  );
}

const STORY_LANG: Record<string, string> = { te: "Telugu", hi: "Hindi", en: "English" };

export default function Landing() {
  const health = useHealth();
  const [kits, setKits] = useState<SampleKit[]>([]);
  useEffect(() => {
    api.samples().then(setKits).catch(() => setKits([]));
  }, []);

  return (
    <div className="min-h-dvh">
      <ModeNotice />
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Brand />
        <nav className="flex items-center gap-1 text-sm font-semibold">
          <Link to="/claim" className="rounded-lg px-3 py-2 text-ink-2 hover:bg-ink/5">Customer app</Link>
          <Link to="/console" className="rounded-lg px-3 py-2 text-ink-2 hover:bg-ink/5">Claims console</Link>
        </nav>
      </header>

      <main className="mx-auto grid max-w-6xl gap-12 px-5 pb-16 pt-6 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:pt-12">
        <section>
          <h1 className="max-w-[18ch] text-[40px] font-extrabold leading-[1.04] tracking-[-0.025em] sm:text-[56px]">
            Motor claims decided in minutes, signed off by a person.
          </h1>
          <p className="mt-5 max-w-[56ch] text-lg leading-relaxed text-ink-2">
            The customer sends a voice note in their own language and a few photos. A team of Gemini agents checks the
            policy, inspects the damage, prices the repair and screens for fraud, then hands the claims officer a
            one-page brief with every number explained.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/claim" className="inline-flex h-12 items-center gap-2 rounded-xl bg-go px-5 font-semibold text-white hover:bg-go-ink">
              <Smartphone className="size-5" /> Report a claim
            </Link>
            <Link to="/console" className="inline-flex h-12 items-center gap-2 rounded-xl border border-line-strong bg-surface px-5 font-semibold hover:border-ink-2">
              <ClipboardCheck className="size-5" /> Open the claims console
            </Link>
          </div>

          {kits.length > 0 && (
            <div className="mt-12">
              <h2 className="text-sm font-semibold text-muted">Try one of three demo stories</h2>
              <ul className="mt-3 divide-y divide-line border-y border-line">
                {kits.map((k) => (
                  <li key={k.key}>
                    <Link to={`/claim?demo=${k.key}`} className="group flex items-center gap-4 py-3.5">
                      <span className="grid size-10 shrink-0 place-items-center rounded-full bg-ink text-sm font-bold text-white">
                        {k.first_name[0]}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold">
                          {k.first_name} · {k.title}
                        </span>
                        <span className="block truncate text-sm text-muted">
                          {STORY_LANG[k.language] ?? k.language_name} · {k.vehicle} · {k.blurb}
                        </span>
                      </span>
                      <ArrowRight className="size-5 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-go" />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="flex flex-col items-center lg:items-start">
          <RoadMap />
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-5 text-[13px] text-muted">
          <span>
            Built on Google Cloud: {health?.model ?? "Gemini"} · Agent Development Kit · {health?.gemma_model ?? "Gemma"} · Cloud Run ·
            Firestore · Cloud Storage
          </span>
          <span>Suraksha General Insurance is a fictional insurer used for this demo.</span>
        </div>
      </footer>
    </div>
  );
}
