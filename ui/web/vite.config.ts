import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const BACKEND_URL = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": BACKEND_URL,
      "/ws": { target: BACKEND_URL, ws: true },
    },
  },
});
