import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Snapshot } from "../api/types";
import { useSnapshotSocket, type ConnectionStatus } from "./useWebSocket";
import { RouteService } from "../services/route.service"

const emptySnapshot: Snapshot = { devices: [], sources: [], sinks: [], zones: [], routes: [] };

interface StateContextValue {
  snapshot: Snapshot;
  connection: ConnectionStatus;
}

const StateContext = createContext<StateContextValue>({
  snapshot: emptySnapshot,
  connection: "connecting",
});

export function StateProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot);
  const onSnapshot = useCallback((next: Snapshot) => setSnapshot(next), []);
  const connection = useSnapshotSocket(onSnapshot);

  useEffect(() => {
    RouteService.getState().then(setSnapshot).catch(() => {});
  }, []);

  return <StateContext.Provider value={{ snapshot, connection }}>{children}</StateContext.Provider>;
}

export const useAppState = () => useContext(StateContext);
