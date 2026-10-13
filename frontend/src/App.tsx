import { createContext, useContext, useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { api, type Health } from "./lib/api";
import Landing from "./pages/Landing";
import CustomerApp from "./pages/customer/CustomerApp";
import Track, { TrackLookup } from "./pages/customer/Track";
import ConsoleLayout from "./pages/console/ConsoleLayout";
import Queue from "./pages/console/Queue";
import ClaimDetail from "./pages/console/ClaimDetail";
import Insights from "./pages/console/Insights";

const HealthContext = createContext<Health | null>(null);
export const useHealth = () => useContext(HealthContext);

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <HealthContext.Provider value={health}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/claim" element={<CustomerApp />} />
        <Route path="/track" element={<TrackLookup />} />
        <Route path="/track/:id" element={<Track />} />
        <Route path="/console" element={<ConsoleLayout />}>
          <Route index element={<Queue />} />
          <Route path="claims/:id" element={<ClaimDetail />} />
          <Route path="insights" element={<Insights />} />
        </Route>
        <Route path="*" element={<Landing />} />
      </Routes>
    </HealthContext.Provider>
  );
}
