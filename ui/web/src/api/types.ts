export type RouteStatus = "active" | "stopped" | "error";

export interface Device {
  id: string;
  name: string;
  platform: string;
  mode: "central" | "local";
  status: "online" | "offline";
  sync_enabled: boolean;
}

export interface Source {
  id: string;
  device_id: string;
  name: string;
  kind: string;
}

export interface Sink {
  id: string;
  device_id: string;
  name: string;
  kind: string;
  zone_id: string | null;
}

export interface Zone {
  id: string;
  name: string;
  sink_ids: string[];
}

export interface Route {
  id: string;
  source_id: string;
  sink_ids: string[];
  transport: string;
  status: RouteStatus;
  error: string | null;
}

export interface Snapshot {
  devices: Device[];
  sources: Source[];
  sinks: Sink[];
  zones: Zone[];
  routes: Route[];
}

export interface CreateRouteRequest {
  source_id: string;
  zone_ids: string[];
  sink_ids: string[];
}
