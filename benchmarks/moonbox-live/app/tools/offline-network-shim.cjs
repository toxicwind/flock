const http = require("node:http");
const https = require("node:https");

function describeTarget(target) {
  if (!target) return "";
  if (typeof target === "string") return target;
  if (target?.href) return target.href;
  const protocol = target?.protocol || "";
  const host = target?.host || target?.hostname || "";
  const path = target?.path || target?.pathname || "";
  return `${protocol || ""}//${host || ""}${path}`;
}

function blockNet(mod, method) {
  const original = mod[method];
  mod[method] = function patched(target, ...args) {
    const url = describeTarget(target);
    throw new Error(`[offline] Network call blocked (${method} ${url || "unknown"})`);
  };
  mod[method].__original = original;
}

blockNet(http, "request");
blockNet(http, "get");
blockNet(https, "request");
blockNet(https, "get");

if (typeof globalThis.fetch === "function") {
  const blockedFetch = (...args) => {
    const target = args[0];
    const url = typeof target === "string" ? target : target?.url || "unknown";
    throw new Error(`[offline] fetch blocked (${url})`);
  };
  blockedFetch.__original = globalThis.fetch;
  globalThis.fetch = blockedFetch;
}
