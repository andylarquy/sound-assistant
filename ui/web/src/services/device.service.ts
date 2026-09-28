import { ApiClient } from "../api/apiClient";
import { Device } from "../api/types";

const setSync = async (deviceId: string, enabled: boolean) => {
  const response = await ApiClient.put<Device>(`/devices/${deviceId}/sync`, { enabled });
  return response.data;
};

export const DeviceService = {
  setSync,
};
