import { ApiClient } from "../api/apiClient";
import { CreateRouteRequest, Route, Snapshot } from "../api/types";

const getState = async () => {
  const snapshot = await ApiClient.get<Snapshot>("/state");
  return snapshot.data;
};

const createRoute = async (body: CreateRouteRequest) => {
  const snapshot = await ApiClient.post<Route>("/routes", body);
  return snapshot.data;
};

const stopRoute = async (routeId: string) => {
  const snapshot = await ApiClient.delete<Route>(`/routes/${routeId}`);
  return snapshot.data;
};

export const RouteService = {
  getState,
  createRoute,
  stopRoute,
};
