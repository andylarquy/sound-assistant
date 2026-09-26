import type { Device, Source } from "../../api/types";
import styles from "../Rows.module.scss";

interface Props {
  sources: Source[];
  devices: Device[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function SourceList({ sources, devices, selectedId, onSelect }: Props) {
  if (sources.length === 0) {
    return <p className={styles.empty}>No sources registered yet. Start an agent.</p>;
  }
  const deviceName = (id: string) => devices.find((d) => d.id === id)?.name ?? id;
  return (
    <div className={styles.list}>
      {sources.map((source) => (
        <div key={source.id} className={styles.row}>
          <input
            type="radio"
            name="source"
            id={`src-${source.id}`}
            checked={selectedId === source.id}
            onChange={() => onSelect(source.id)}
          />
          <label htmlFor={`src-${source.id}`}>{source.name}</label>
          <span className={styles.meta}>{deviceName(source.device_id)}</span>
        </div>
      ))}
    </div>
  );
}
