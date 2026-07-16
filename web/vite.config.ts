import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// The SPA is served under /app/ by the Python server (nr ui). Game data (/api)
// and extracted assets (/assets) come from that same server; in dev we proxy
// them to a locally-running `nr ui` (port 8391).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  base: "/app/",
  server: {
    port: 5178,
    proxy: {
      "/api": "http://127.0.0.1:8391",
      "/assets": "http://127.0.0.1:8391",
    },
  },
  build: {
    outDir: "../nightreign/ui/static/app",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1400,
  },
});
