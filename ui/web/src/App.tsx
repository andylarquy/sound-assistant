import { useState } from "react";
import styles from "./App.module.scss";
import { DestinationList } from "./components/DestinationList/DestinationList";
import { Panel } from "./components/Panel/Panel";
import { RouteList } from "./components/RouteList/RouteList";
import { SourceList } from "./components/SourceList/SourceList";
import { StatusBadge } from "./components/StatusBadge/StatusBadge";
import { useAppState } from "./state/StateProvider";
import { RouteService } from "./services/route.service"

const messageOf = (e: unknown) => (e instanceof Error ? e.message : "Request failed");

export function App() {
  const { snapshot, connection } = useAppState();
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [zoneIds, setZoneIds] = useState<string[]>([]);
  const [sinkIds, setSinkIds] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const canRoute = !!sourceId && (zoneIds.length > 0 || sinkIds.length > 0) && !pending;

  const createRoute = async () => {
    if (!sourceId) return;
    setError("");
    setPending(true);
    try {
      await RouteService.createRoute({ source_id: sourceId, zone_ids: zoneIds, sink_ids: sinkIds });
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setPending(false);
    }
  };

  const stopRoute = (id: string) => {
    setError("");
    RouteService.stopRoute(id).catch((e) => setError(messageOf(e)));
  };

  return (
    <>
      <header className={styles.header}>
        <h1>Sound Assistant</h1>
        <StatusBadge status={connection} />
      </header>
      <main className={styles.main}>
        <Panel title="Source">
          <SourceList
            sources={snapshot.sources}
            devices={snapshot.devices}
            selectedId={sourceId}
            onSelect={setSourceId}
          />
        </Panel>
        <Panel title="Destinations">
          <DestinationList
            zones={snapshot.zones}
            sinks={snapshot.sinks}
            devices={snapshot.devices}
            selectedZoneIds={zoneIds}
            selectedSinkIds={sinkIds}
            onZonesChange={setZoneIds}
            onSinksChange={setSinkIds}
          />
          <button className={styles.routeButton} disabled={!canRoute} onClick={createRoute}>
            ROUTE
          </button>
          <p className={styles.error}>{error}</p>
        </Panel>
        <Panel title="Current routes" className={styles.wide}>
          <RouteList
            routes={snapshot.routes}
            sources={snapshot.sources}
            sinks={snapshot.sinks}
            onStop={stopRoute}
          />
        </Panel>
      </main>
    </>
  );
}
