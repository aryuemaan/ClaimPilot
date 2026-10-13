import { ArrowLeft, Camera, FileText, Keyboard, Mic, Plus, Sparkles, Square, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import CustomerShell, { LangProvider } from "../../components/CustomerShell";
import { Button, ErrorNote, Spinner } from "../../components/ui";
import { api, type Policy, type SampleKit } from "../../lib/api";
import { cx, shortDate } from "../../lib/format";
import { asLang, fill, useLang } from "../../lib/i18n";
import { startRecording, type Recording } from "../../lib/recorder";

type Pick = { id: string; file: File; kind: "photo" | "document"; url: string };

// crypto.randomUUID only exists on HTTPS/localhost; this works on plain-HTTP LAN demos too.
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export default function CustomerApp() {
  return (
    <LangProvider>
      <CustomerShell>
        <Flow />
      </CustomerShell>
    </LangProvider>
  );
}

function Steps({ step }: { step: number }) {
  const { t } = useLang();
  const labels = [t.step1, t.step2, t.step3];
  return (
    <ol className="mb-6 grid grid-cols-3 gap-2" aria-label="Progress">
      {labels.map((l, i) => (
        <li key={l} className="min-w-0">
          <span className={cx("block h-1 rounded-full", i + 1 <= step ? "bg-go" : "bg-ink/10")} />
          <span className={cx("mt-1.5 block truncate text-[11px] font-semibold", i + 1 === step ? "text-ink" : "text-muted")}>
            {i + 1}. {l}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Flow() {
  const { t, setLang } = useLang();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [kits, setKits] = useState<SampleKit[]>([]);
  const [kit, setKit] = useState<SampleKit | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [step, setStep] = useState(0);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [statement, setStatement] = useState("");
  const [english, setEnglish] = useState("");
  const [transcript, setTranscript] = useState<{ transcript: string; english: string; language: string } | null>(null);
  const [voice, setVoice] = useState<Blob | null>(null);
  const [typing, setTyping] = useState(false);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [consent, setConsent] = useState(false);

  const choose = async (p: Policy, k?: SampleKit | null) => {
    setPolicy(p);
    setKit(k ?? null);
    setLang(asLang(p.language));
    setStep(1);
    window.scrollTo({ top: 0 });
  };

  useEffect(() => {
    api.samples().then((ks) => {
      setKits(ks);
      const demo = params.get("demo");
      const k = ks.find((x) => x.key === demo);
      if (k) api.lookupPolicy(k.policy_number).then((p) => choose(p, k)).catch(() => {});
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const find = async (q: string, k?: SampleKit) => {
    setError("");
    setBusy(true);
    try {
      const p = await api.lookupPolicy(q);
      await choose(p, k ?? kits.find((x) => x.policy_number === p.policy_number) ?? null);
    } catch {
      setError(t.notFound);
    } finally {
      setBusy(false);
    }
  };

  const addFiles = (files: FileList | File[], kind: Pick["kind"]) => {
    const next = Array.from(files).map((file) => ({ id: uid(), file, kind, url: URL.createObjectURL(file) }));
    setPicks((p) => [...p, ...next].slice(0, 12));
  };

  const useSampleFiles = async () => {
    if (!kit) return;
    setBusy(true);
    try {
      const files = await Promise.all(kit.files.map(async (f) => ({ f, file: await api.sampleFile(kit.key, f.name, f.mime) })));
      setPicks(files.map(({ f, file }) => ({ id: uid(), file, kind: f.kind, url: URL.createObjectURL(file) })));
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!policy) return;
    if (!statement.trim() && picks.length === 0) {
      setError(t.noStory);
      return;
    }
    setError("");
    setBusy(true);
    const fd = new FormData();
    fd.append("policy_number", policy.policy_number);
    fd.append("statement", statement);
    fd.append("language", policy.language);
    if (transcript) fd.append("transcript", JSON.stringify(transcript));
    for (const p of picks) {
      fd.append("files", p.file, p.file.name);
      fd.append("kinds", p.kind);
    }
    if (voice) {
      fd.append("files", voice, "voice-note.wav");
      fd.append("kinds", "voice");
    }
    try {
      const { claim_id } = await api.createClaim(fd);
      nav(`/track/${claim_id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  // -------------------------------------------------------------------------
  if (step === 0) {
    return (
      <div>
        <h1 className="text-[28px] font-extrabold leading-tight tracking-tight">{t.tagline}</h1>
        <form
          className="mt-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (query.trim()) find(query.trim());
          }}
        >
          <label htmlFor="q" className="text-sm font-semibold">
            {t.findPolicy}
          </label>
          <p className="text-[13px] text-muted">{t.findPolicyHint}</p>
          <input
            id="q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="SGI-PC-25-118204"
            autoComplete="off"
            className="mt-1.5 h-12 w-full rounded-xl border border-line-strong bg-surface px-4 text-base outline-none placeholder:text-muted focus:border-go"
          />
          <Button type="submit" size="lg" className="mt-3 w-full" loading={busy && !kit} disabled={!query.trim()}>
            {t.continue}
          </Button>
        </form>
        <div className="mt-3">
          <ErrorNote>{error}</ErrorNote>
        </div>
        {kits.length > 0 && (
          <section className="mt-8">
            <h2 className="text-sm font-semibold text-muted">{t.demoPolicyholders}</h2>
            <ul className="mt-2 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
              {kits.map((k) => (
                <li key={k.key}>
                  <button onClick={() => find(k.policy_number, k)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-paper">
                    <span className="grid size-10 shrink-0 place-items-center rounded-full bg-ink font-bold text-white">{k.first_name[0]}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold">
                        {k.holder_name} <span className="font-normal text-muted">· {k.language_name}</span>
                      </span>
                      <span className="block truncate text-[13px] text-muted">
                        {k.vehicle} · {k.title}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    );
  }

  const header = policy && (
    <div className="mb-5">
      <button onClick={() => setStep(step - 1)} className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-ink-2 hover:text-ink">
        <ArrowLeft className="size-4" /> {t.back}
      </button>
      <p className="text-[15px] font-semibold">{fill(t.hi, { name: policy.first_name })}</p>
      <p className="text-[13px] text-muted">
        {fill(t.coveredUntil, { vehicle: `${policy.vehicle.make_model} (${policy.vehicle.registration})`, date: shortDate(policy.end_date) })}
      </p>
    </div>
  );

  if (step === 1) {
    return (
      <div>
        {header}
        <Steps step={1} />
        <h1 className="text-2xl font-extrabold tracking-tight">{t.step1}</h1>
        <p className="mt-1 text-[15px] text-ink-2">{t.step1Hint}</p>

        {!typing && (
          <VoiceRecorder
            language={policy?.language ?? "en"}
            onResult={(r, blob) => {
              setTranscript(r);
              setStatement(r.transcript);
              setEnglish(r.english);
              setVoice(blob);
            }}
            onFallback={() => setTyping(true)}
          />
        )}

        {(typing || statement) && (
          <div className="mt-5">
            <label htmlFor="story" className="text-sm font-semibold">
              {t.yourWords}
            </label>
            <textarea
              id="story"
              value={statement}
              onChange={(e) => {
                setStatement(e.target.value);
                setEnglish("");
              }}
              rows={6}
              placeholder={t.storyPlaceholder}
              className="mt-1.5 w-full rounded-xl border border-line-strong bg-surface px-4 py-3 text-[15px] leading-relaxed outline-none focus:border-go"
            />
            {english && english !== statement && (
              <div className="mt-2 rounded-xl bg-ink/[0.04] px-4 py-3">
                <p className="text-xs font-semibold text-muted">{t.inEnglish}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-2">{english}</p>
              </div>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2">
          {!typing && !statement && (
            <button onClick={() => setTyping(true)} className="inline-flex items-center gap-1.5 text-sm font-semibold text-go-ink hover:underline">
              <Keyboard className="size-4" /> {t.typeInstead}
            </button>
          )}
          {kit && (
            <button
              onClick={() => {
                setStatement(kit.statement);
                setEnglish("");
                setTyping(true);
              }}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-go-ink hover:underline"
            >
              <Sparkles className="size-4" /> {t.useSampleStory}
            </button>
          )}
        </div>

        <Button size="lg" className="mt-8 w-full" onClick={() => setStep(2)}>
          {t.next}
        </Button>
      </div>
    );
  }

  if (step === 2) {
    const photos = picks.filter((p) => p.kind === "photo");
    const docs = picks.filter((p) => p.kind === "document");
    return (
      <div>
        {header}
        <Steps step={2} />
        <h1 className="text-2xl font-extrabold tracking-tight">{t.step2}</h1>
        <p className="mt-1 text-[15px] text-ink-2">{t.step2Hint}</p>

        <h2 className="mt-6 text-sm font-semibold">{t.photos}</h2>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {photos.map((p) => (
            <Thumb key={p.id} pick={p} onRemove={() => setPicks((all) => all.filter((x) => x.id !== p.id))} />
          ))}
          <FileTile label={t.addPhotos} icon={<Camera className="size-6" />} accept="image/*" capture onFiles={(f) => addFiles(f, "photo")} />
        </div>

        <h2 className="mt-6 text-sm font-semibold">{t.documents}</h2>
        <div className="mt-2 space-y-2">
          {docs.map((p) => (
            <div key={p.id} className="flex items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2">
              {p.file.type.startsWith("image/") ? (
                <img src={p.url} alt="" className="size-10 rounded object-cover" />
              ) : (
                <FileText className="size-10 p-2 text-muted" />
              )}
              <span className="min-w-0 flex-1 truncate text-sm">{p.file.name}</span>
              <button onClick={() => setPicks((all) => all.filter((x) => x.id !== p.id))} aria-label="Remove" className="rounded p-1 text-muted hover:bg-ink/5">
                <X className="size-4" />
              </button>
            </div>
          ))}
          <label className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-line-strong text-sm font-semibold text-ink-2 hover:border-go hover:text-go-ink">
            <Plus className="size-4" /> {t.addDocs}
            <input type="file" accept="image/*,application/pdf" multiple className="sr-only" onChange={(e) => e.target.files && addFiles(e.target.files, "document")} />
          </label>
        </div>

        {kit && picks.length === 0 && (
          <button onClick={useSampleFiles} className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-go-ink hover:underline">
            {busy ? <Spinner /> : <Sparkles className="size-4" />} {t.useSampleFiles}
          </button>
        )}

        <Button size="lg" className="mt-8 w-full" onClick={() => setStep(3)}>
          {t.next}
        </Button>
      </div>
    );
  }

  // step 3
  return (
    <div>
      {header}
      <Steps step={3} />
      <h1 className="text-2xl font-extrabold tracking-tight">{t.step3}</h1>
      <div className="mt-4 divide-y divide-line rounded-xl border border-line bg-surface">
        <div className="px-4 py-3">
          <p className="text-xs font-semibold text-muted">{t.step1}</p>
          <p className="mt-1 line-clamp-4 text-[15px] leading-relaxed">{statement || "—"}</p>
        </div>
        <div className="px-4 py-3">
          <p className="text-xs font-semibold text-muted">{t.photos}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {picks.filter((p) => p.kind === "photo").map((p) => (
              <img key={p.id} src={p.url} alt="" className="size-14 rounded-lg object-cover" />
            ))}
            {picks.filter((p) => p.kind === "photo").length === 0 && <span className="text-sm text-muted">—</span>}
          </div>
        </div>
        <div className="px-4 py-3">
          <p className="text-xs font-semibold text-muted">{t.documents}</p>
          <p className="mt-1 text-sm">{picks.filter((p) => p.kind === "document").map((p) => p.file.name).join(", ") || "—"}</p>
        </div>
      </div>
      <label className="mt-5 flex items-start gap-3 text-sm leading-relaxed text-ink-2">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 size-4 accent-[#0B6E4F]" />
        {t.consent}
      </label>
      <div className="mt-4">
        <ErrorNote>{error}</ErrorNote>
      </div>
      <Button size="lg" className="mt-6 w-full" disabled={!consent} loading={busy} onClick={submit}>
        {busy ? t.submitting : t.submit}
      </Button>
    </div>
  );
}

function Thumb({ pick, onRemove }: { pick: Pick; onRemove: () => void }) {
  return (
    <div className="relative aspect-square overflow-hidden rounded-xl bg-night">
      <img src={pick.url} alt={pick.file.name} className="size-full object-cover" />
      <button onClick={onRemove} aria-label={`Remove ${pick.file.name}`} className="absolute right-1 top-1 grid size-7 place-items-center rounded-full bg-black/60 text-white">
        <X className="size-4" />
      </button>
    </div>
  );
}

function FileTile({ label, icon, accept, capture, onFiles }: { label: string; icon: React.ReactNode; accept: string; capture?: boolean; onFiles: (f: FileList) => void }) {
  return (
    <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed border-line-strong bg-surface p-2 text-center text-[12px] font-semibold text-ink-2 hover:border-go hover:text-go-ink">
      {icon}
      {label}
      <input type="file" accept={accept} multiple {...(capture ? { capture: "environment" as const } : {})} className="sr-only" onChange={(e) => e.target.files && onFiles(e.target.files)} />
    </label>
  );
}

function VoiceRecorder({
  language,
  onResult,
  onFallback,
}: {
  language: string;
  onResult: (r: { transcript: string; english: string; language: string }, blob: Blob) => void;
  onFallback: () => void;
}) {
  const { t } = useLang();
  const [state, setState] = useState<"idle" | "recording" | "transcribing">("idle");
  const [seconds, setSeconds] = useState(0);
  const [levels, setLevels] = useState<number[]>(Array(24).fill(0.05));
  const [error, setError] = useState("");
  const rec = useRef<Recording | null>(null);
  const raf = useRef<number>(0);

  useEffect(() => () => {
    cancelAnimationFrame(raf.current);
    rec.current?.cancel();
  }, []);

  const start = async () => {
    setError("");
    try {
      rec.current = await startRecording();
    } catch {
      setError(t.micBlocked);
      onFallback();
      return;
    }
    setState("recording");
    setSeconds(0);
    const t0 = performance.now();
    let last = 0;
    const tick = (now: number) => {
      if (now - last > 90 && rec.current) {
        last = now;
        setSeconds(Math.floor((now - t0) / 1000));
        setLevels((l) => [...l.slice(1), Math.max(0.05, rec.current!.level())]);
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  };

  const stop = async () => {
    cancelAnimationFrame(raf.current);
    if (!rec.current) return;
    setState("transcribing");
    try {
      const blob = await rec.current.stop();
      rec.current = null;
      const r = await api.transcribe(blob, language);
      onResult(r, blob);
      setState("idle");
    } catch (e) {
      setError((e as Error).message);
      setState("idle");
      onFallback();
    }
  };

  return (
    <div className="mt-6 flex flex-col items-center rounded-2xl border border-line bg-surface px-4 py-7">
      <button
        onClick={state === "recording" ? stop : start}
        disabled={state === "transcribing"}
        aria-label={state === "recording" ? t.recording : t.tapToRecord}
        className={cx(
          "grid size-24 place-items-center rounded-full text-white transition-colors",
          state === "recording" ? "recording-ring bg-stop" : "bg-go hover:bg-go-ink",
          state === "transcribing" && "bg-ink",
        )}
      >
        {state === "recording" ? <Square className="size-8" fill="currentColor" /> : state === "transcribing" ? <Spinner className="size-8" /> : <Mic className="size-10" />}
      </button>
      <div className="mt-4 flex h-8 items-end gap-[3px]" aria-hidden>
        {levels.map((l, i) => (
          <span key={i} className={cx("w-1.5 rounded-full", state === "recording" ? "bg-stop" : "bg-ink/15")} style={{ height: `${Math.round(6 + l * 26)}px` }} />
        ))}
      </div>
      <p className="mt-3 text-sm font-semibold text-ink-2">
        {state === "recording" ? `${t.recording} ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}` : state === "transcribing" ? t.transcribing : t.tapToRecord}
      </p>
      {error && <p className="mt-2 max-w-xs text-center text-[13px] text-stop">{error}</p>}
    </div>
  );
}
