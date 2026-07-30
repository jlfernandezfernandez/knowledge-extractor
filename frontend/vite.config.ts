import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": { target: "http://api:8000", changeOrigin: true },
      "/ws": { target: "http://api:8000", changeOrigin: true, ws: true },
    },
  },
  // Deep links like /review/<id> are resolved client-side; Vite's dev server
  // and any static host must fall back to index.html for unknown paths.
  appType: "spa",
});
