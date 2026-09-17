import { serve } from "bun";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

const publicDir = join(import.meta.dir, "../public");
const dataDir = join(import.meta.dir, "../data");

serve({
  port: 3000,
  async fetch(req) {
    const url = new URL(req.url);
    let path = url.pathname;
    if (path === "/") path = "/index.html";
    
    // API endpoint for consolidated data
    if (path === "/api/data") {
      const dataPath = join(dataDir, "consolidated.json");
      if (existsSync(dataPath)) {
        return new Response(readFileSync(dataPath), { headers: { "Content-Type": "application/json" } });
      }
      // fallback to md parsed
      return new Response(JSON.stringify({ error: "Run save-all first" }), { status: 404 });
    }
    if (path === "/api/manifest") {
      const mp = join(dataDir, "manifest.json");
      if (existsSync(mp)) {
        return new Response(readFileSync(mp), { headers: { "Content-Type": "application/json" } });
      }
      return new Response("[]", { headers: { "Content-Type": "application/json" } });
    }
    
    const filePath = join(publicDir, path);
    if (existsSync(filePath)) {
      const ext = filePath.split(".").pop();
      const mime: Record<string,string> = {
        html: "text/html", js: "application/javascript", css: "text/css",
        json: "application/json", md: "text/markdown"
      };
      return new Response(readFileSync(filePath), { headers: { "Content-Type": mime[ext||""]||"text/plain" } });
    }
    return new Response("Not found", { status: 404 });
  }
});

console.log("🚀 Dashboard at http://localhost:3000");
