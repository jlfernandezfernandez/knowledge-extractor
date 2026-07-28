import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  // Deep links like /review/<id> are resolved client-side; Vite's dev server
  // and any static host must fall back to index.html for unknown paths.
  appType: "spa",
});
