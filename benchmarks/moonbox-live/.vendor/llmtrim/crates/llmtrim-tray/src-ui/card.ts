import { invoke } from "@tauri-apps/api/core";

import type { AgentCard, ChildCard } from "./types.js";
import { el } from "./dom.js";
import { sparkline } from "./sparkline.js";
import { type TreeNode, caret as caretIcon, collapsible, wireExpander } from "./tree.js";
import { formatBill, formatPct, formatRelative, formatTokens } from "./format.js";

// A single agent row. The savings bar gradient is the one decorative gradient
// (a meter fill, not gradient text); width encodes saved_pct directly. The whole
// header is the disclosure toggle: clicking anywhere on it lazily drills into
// projects (`get_agent_projects`) and then sessions (`get_project_sessions`) —
// nothing is fetched until the card is first expanded.
export function agentCard(card: AgentCard): HTMLElement {
  const hasData = card.has_savings_data;
  const pct = Math.max(0, Math.min(100, card.saved_pct));

  // --- header: the whole row is the toggle button (caret is the affordance) ---
  const name = el("span", { class: "card-name" }, [card.display_name]);
  const when = el("span", { class: "card-when" }, [formatRelative(card.last_event_ts)]);
  const head = el(
    "button",
    { class: "card-head", type: "button", "aria-label": `Toggle ${card.display_name} projects` },
    [el("span", { class: "card-caret" }, [caretIcon()]), name, when],
  );

  // --- lazy project → session drill-down ---
  const { region: children, mount } = collapsible();
  wireExpander(head, children, mount, () => loadProjects(card.agent), 0);

  // --- savings meter ---
  const fill = el("div", { class: "meter-fill" });
  // Drive the bar with a 0..1 scaleX (compositor-only) rather than width.
  fill.style.setProperty("--fill", String(pct / 100));
  if (!hasData) fill.classList.add("meter-empty");
  const meter = el(
    "div",
    {
      class: "meter",
      role: "progressbar",
      "aria-valuemin": "0",
      "aria-valuemax": "100",
      ...(hasData ? { "aria-valuenow": String(Math.round(pct)) } : {}),
      "aria-label": "input saved",
    },
    [fill],
  );

  const pctLabel = el(
    "span",
    { class: hasData ? "card-pct" : "card-pct card-pct-empty" },
    [formatPct(card.saved_pct, hasData)],
  );
  const savedTag = el("span", { class: "card-tag" }, ["saved"]);
  const pctBlock = el("div", { class: "card-pct-block" }, [pctLabel, savedTag]);

  const meterRow = el("div", { class: "card-meter-row" }, [meter, pctBlock]);

  // --- stats: bill, cache, sparkline ---
  const bill = stat(formatBill(card.bill_micros), "billed");
  const cache = stat(formatTokens(card.cache_read_tokens), "cache reads");
  // Gradient id keyed on the agent (slugified), not the array index, so it
  // stays unique and stable across re-renders that reorder the cards.
  const gradId = `spark-grad-${card.agent.replace(/[^a-z0-9]/gi, "-")}`;
  const spark = el("div", { class: "card-spark" }, [sparkline(card.trend, gradId)]);
  const stats = el("div", { class: "card-stats" }, [bill, cache, spark]);

  const article = el("article", { class: "card" }, [head, meterRow, stats, children]);

  // Whole-card click toggles the drill-down: a click on the summary (meter,
  // stats, spark) forwards to the header, which owns the aria-expanded state.
  // Clicks inside the children region are the project/session rows' own — leave
  // them, and don't re-fire on the header itself (its native click already ran).
  article.addEventListener("click", (e) => {
    const target = e.target as Node;
    if (head.contains(target) || children.contains(target)) return;
    head.click();
  });

  return article;
}

// Level-2 loader: an agent's projects, each of which loads its own sessions
// (level 3, leaves) on expand. `p.key`/`s` keys round-trip the follow-up query.
async function loadProjects(agent: string): Promise<TreeNode[]> {
  const projects = await invoke<ChildCard[]>("get_agent_projects", { agent });
  return projects.map((p) => ({
    card: p,
    loadChildren: async () => {
      const sessions = await invoke<ChildCard[]>("get_project_sessions", {
        agent,
        project: p.key,
      });
      return sessions.map((s) => ({ card: s }));
    },
  }));
}

function stat(value: string, label: string): HTMLElement {
  return el("div", { class: "stat" }, [
    el("span", { class: "stat-value" }, [value]),
    el("span", { class: "stat-label" }, [label]),
  ]);
}
