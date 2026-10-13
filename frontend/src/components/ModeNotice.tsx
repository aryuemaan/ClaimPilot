import { useHealth } from "../App";

/** Shown only when the backend runs without Gemini credentials. */
export default function ModeNotice() {
  const health = useHealth();
  if (!health || health.mode !== "offline") return null;
  return (
    <div className="bg-amber-tint px-4 py-1.5 text-center text-[13px] text-amber">
      <strong className="font-semibold">Offline demo mode.</strong> A scripted model stands in for Gemini. Add a GOOGLE_API_KEY
      to run the live agents.
    </div>
  );
}
