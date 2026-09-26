import type { Route, Sink, Source } from "../../api/types";
import rows from "../Rows.module.scss";
import styles from "./RouteList.module.scss";

interface Props {
  routes: Route[];
  sources: Source[];
  sinks: Sink[];
  onStop: (routeId: string) => void;
}

export function RouteList({ routes, sources, sinks, onStop }: Props) {
  const visible = routes.filter((r) => r.status !== "stopped");
  if (visible.length === 0) return <p className={rows.empty}>No active routes.</p>;

  return (
    <div className={rows.list}>
      {visible.map((route) => {
        const source = sources.find((s) => s.id === route.source_id);
        const sinkNames = route.sink_ids
          .map((id) => sinks.find((s) => s.id === id)?.name ?? id)
          .join(", ");
        return (
          <div key={route.id} className={styles.card}>
            <div>
              <strong>{source?.name ?? route.source_id}</strong> &rarr; {sinkNames}
              <div className={route.status === "active" ? styles.active : styles.error}>
                {route.status}
                {route.error ? `: ${route.error}` : ""}
              </div>
            </div>
            <button onClick={() => onStop(route.id)}>Stop</button>
          </div>
        );
      })}
    </div>
  );
}
