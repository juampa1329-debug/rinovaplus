import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const liveDevelopment = process.env.CRM_LIVE_DEVELOPMENT === "true";

export default defineConfig({
  envDir: liveDevelopment ? false : undefined,
  cacheDir: liveDevelopment ? "/tmp/crm-vite" : undefined,
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    watch: liveDevelopment ? { usePolling: true, interval: 500 } : undefined,
    proxy: {
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/catalog": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/ai": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/ai": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/campaigns": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/broadcasts": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/crm": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/local": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    proxy: {
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/catalog": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/ai": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/ai": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/campaigns": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/broadcasts": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/v1/crm": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api/local": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    maxWorkers: 2,
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
  },
});
