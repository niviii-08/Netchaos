import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the browser talks to Vite, which forwards /api to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_PROXY_TARGET || "http://localhost:8000" },
  },
});
