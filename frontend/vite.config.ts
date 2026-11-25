import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, anything starting with /api is forwarded to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
