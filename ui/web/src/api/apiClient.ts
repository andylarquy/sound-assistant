import axios, { AxiosError } from "axios";
import type { CreateRouteRequest, Route, Snapshot } from "./types";

export class ApiError extends Error {}

export const ApiClient = axios.create({ baseURL: "/api" });

ApiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) =>
    Promise.reject(new ApiError(error.response?.data?.detail ?? error.message)),
);

export const api = {
  getState: async () => (await ApiClient.get<Snapshot>("/state")).data,
  createRoute: async (body: CreateRouteRequest) => ApiClient.post<Route>("/routes", body).then((r) => r.data),
  stopRoute: (routeId: string) => ApiClient.delete<Route>(`/routes/${routeId}`).then((r) => r.data),
};
