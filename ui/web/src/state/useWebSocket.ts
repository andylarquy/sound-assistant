import { useEffect, useState } from "react";
import type { Snapshot } from "../api/types";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

export function useSnapshotSocket(onSnapshot: (snapshot: Snapshot) => void): ConnectionStatus {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry: number | undefined;
    let disposed = false;

    const connect = () => {
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${protocol}//${location.host}/ws`);
      ws.onopen = () => setStatus("connected");
      ws.onclose = () => {
        setStatus("disconnected");
        if (!disposed) retry = window.setTimeout(connect, 2000);
      };
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "state") onSnapshot(message.data as Snapshot);
      };
    };

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(retry);
      ws?.close();
    };
  }, [onSnapshot]);

  return status;
}
