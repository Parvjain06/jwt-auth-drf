import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the React dev server forwards /api to Django on port 8000,
// so the browser sees one origin (no CORS, session cookies just work).
// `npm run build` writes the app into ../backend/frontend_dist, which Django serves.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    outDir: "../backend/frontend_dist",
    emptyOutDir: true,
    assetsDir: "assets",
  },
});
