import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { DICTS, LANG_LABEL, LangContext, useLang, type Lang } from "../lib/i18n";
import { cx } from "../lib/format";
import ModeNotice from "./ModeNotice";
import { Brand } from "./ui";

function readLang(): Lang {
  try {
    const v = sessionStorage.getItem("cp-lang");
    return v === "hi" || v === "te" ? v : "en";
  } catch {
    return "en";
  }
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readLang);
  const value = useMemo(
    () => ({
      lang,
      t: DICTS[lang],
      setLang: (l: Lang) => {
        setLangState(l);
        try {
          sessionStorage.setItem("cp-lang", l);
        } catch {
          /* storage unavailable */
        }
      },
    }),
    [lang],
  );
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <div className="flex rounded-lg border border-line bg-surface p-0.5" role="group" aria-label="Language">
      {(Object.keys(LANG_LABEL) as Lang[]).map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={cx("rounded-md px-2 py-1 text-xs font-semibold", lang === l ? "bg-ink text-white" : "text-ink-2 hover:bg-ink/5")}
        >
          {LANG_LABEL[l]}
        </button>
      ))}
    </div>
  );
}

export default function CustomerShell({ children, wide }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-dvh bg-paper">
      <ModeNotice />
      <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
        <div className={cx("mx-auto flex items-center justify-between px-4 py-3", wide ? "max-w-2xl" : "max-w-[460px]")}>
          <Link to="/" aria-label="ClaimPilot home">
            <Brand />
          </Link>
          <LangSwitch />
        </div>
      </header>
      <main className={cx("mx-auto px-4 pb-24 pt-5", wide ? "max-w-2xl" : "max-w-[460px]")}>{children}</main>
    </div>
  );
}
