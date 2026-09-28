import type { Device, Source } from "../../api/types";
import styles from "../Rows.module.scss";

interface Props {
  sources: Source[];
  devices: Device[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onSyncToggle: (deviceId: string, enabled: boolean) => void;
}

export function SourceList({ sources, devices, selectedId, onSelect, onSyncToggle }: Props) {
  if (sources.length === 0) {
    return <p className={styles.empty}>No sources registered yet. Start an agent.</p>;
  }
  const deviceOf = (id: string) => devices.find((d) => d.id === id);
  return (
    <div className={styles.list}>
      {sources.map((source) => {
        const device = deviceOf(source.device_id);
        return (
          <div key={source.id} className={styles.row}>
            <input
              type="radio"
              name="source"
              id={`src-${source.id}`}
              checked={selectedId === source.id}
              onChange={() => onSelect(source.id)}
            />
            <label htmlFor={`src-${source.id}`}>{source.name}</label>
            <span className={styles.meta}>{device?.name ?? source.device_id}</span>
            {device?.platform === "windows" && (
              <label className={styles.meta} title="Play this device's own speakers in sync with networked destinations, via a virtual audio cable">
                <input
                  type="checkbox"
                  checked={device.sync_enabled}
                  onChange={(e) => onSyncToggle(device.id, e.target.checked)}
                />{" "}
                Sync
              </label>
            )}
          </div>
        );
      })}
    </div>
  );
}
