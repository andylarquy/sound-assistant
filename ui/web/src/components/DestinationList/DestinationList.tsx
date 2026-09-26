import type { Device, Sink, Zone } from "../../api/types";
import styles from "../Rows.module.scss";

interface Props {
  zones: Zone[];
  sinks: Sink[];
  devices: Device[];
  selectedZoneIds: string[];
  selectedSinkIds: string[];
  onZonesChange: (ids: string[]) => void;
  onSinksChange: (ids: string[]) => void;
}

const toggle = (ids: string[], id: string) =>
  ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];

export function DestinationList(props: Props) {
  const { zones, sinks, devices, selectedZoneIds, selectedSinkIds } = props;
  const unzoned = sinks.filter((s) => !s.zone_id);
  const deviceName = (id: string) => devices.find((d) => d.id === id)?.name ?? id;

  if (zones.length === 0 && unzoned.length === 0) {
    return <p className={styles.empty}>No zones or sinks registered yet.</p>;
  }

  return (
    <div className={styles.list}>
      {zones.map((zone) => (
        <div key={zone.id} className={styles.row}>
          <input
            type="checkbox"
            id={`zone-${zone.id}`}
            checked={selectedZoneIds.includes(zone.id)}
            onChange={() => props.onZonesChange(toggle(selectedZoneIds, zone.id))}
          />
          <label htmlFor={`zone-${zone.id}`}>{zone.name}</label>
          <span className={styles.meta}>{zone.sink_ids.length} sink(s)</span>
        </div>
      ))}
      {unzoned.map((sink) => (
        <div key={sink.id} className={styles.row}>
          <input
            type="checkbox"
            id={`sink-${sink.id}`}
            checked={selectedSinkIds.includes(sink.id)}
            onChange={() => props.onSinksChange(toggle(selectedSinkIds, sink.id))}
          />
          <label htmlFor={`sink-${sink.id}`}>{sink.name}</label>
          <span className={styles.meta}>{deviceName(sink.device_id)}</span>
        </div>
      ))}
    </div>
  );
}
