import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
    root: "frontend",
    base: "/static/frontend/",
    plugins: [react(), tailwindcss()],
    build: {
        outDir: "../static/frontend",
        emptyOutDir: true,
    },
});
