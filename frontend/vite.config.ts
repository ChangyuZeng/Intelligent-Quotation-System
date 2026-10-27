import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 构建产物直接落到后端静态目录，由 FastAPI 在同一个端口托管。
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "../../server/static",
    emptyOutDir: true,
    assetsDir: "assets",
    target: "es2020",
    sourcemap: false,
  },
  server: {
    port: 3000,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
