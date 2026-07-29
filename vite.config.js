import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
    root: "frontend",
    base: "/static/frontend/",
    plugins: [react(), tailwindcss()],
    server: {
        proxy: {
            "/api": "http://127.0.0.1:5050",
            "/diagnose": "http://127.0.0.1:5050",
        },
    },
    build: {
        outDir: "../static/frontend",
        emptyOutDir: true,
    },
});
