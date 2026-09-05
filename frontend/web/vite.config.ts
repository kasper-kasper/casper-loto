import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({base:"/web/",plugins:[react()],server:{port:5175,proxy:{"/api":{target:"http://127.0.0.1:8000"}}},test:{environment:"jsdom",setupFiles:"./src/test/setup.ts"}});
