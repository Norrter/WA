import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // 5173 разрешён в CORS бэкенда по умолчанию
    port: 5173,
    strictPort: true,
    // Проект лежит на диске Windows (/mnt/c), а WSL не получает оттуда
    // события об изменении файлов. Опрос нужен, чтобы страница
    // обновлялась после правок кода.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
});
