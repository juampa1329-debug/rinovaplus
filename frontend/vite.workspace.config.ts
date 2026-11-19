import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
const buildId = String(Date.now());
export default defineConfig({
  envDir: false,
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "rinova-build-version",
      transformIndexHtml: () => [
        {
          tag: "meta",
          attrs: { name: "rinova-build", content: buildId },
          injectTo: "head",
        },
      ],
      generateBundle() {
        this.emitFile({
          type: "asset",
          fileName: "frontend-version.json",
          source: JSON.stringify({ build: buildId }),
        });
      },
    },
  ],
  build: {
    outDir: "dist-workspace",
    rollupOptions: { input: "workspace.html" },
  },
});
