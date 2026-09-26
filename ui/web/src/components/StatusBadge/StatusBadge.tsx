import type { ConnectionStatus } from "../../state/useWebSocket";
import styles from "./StatusBadge.module.scss";

export function StatusBadge({ status }: { status: ConnectionStatus }) {
  const cls = [
    styles.badge,
    status === "connected" && styles.connected,
    status === "disconnected" && styles.disconnected,
  ]
    .filter(Boolean)
    .join(" ");
  return <span className={cls}>{status}</span>;
}
