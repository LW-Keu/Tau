import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// tau API 无 CORS 头,开发期经 vite 代理同源访问。
// 后端不在默认端口时改这里,或改 App 设置里的 Base URL 直连(需后端加 CORS)。
const API_ORIGIN = "http://127.0.0.1:8642";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/v1": API_ORIGIN,
      "/health": API_ORIGIN,
    },
  },
});
