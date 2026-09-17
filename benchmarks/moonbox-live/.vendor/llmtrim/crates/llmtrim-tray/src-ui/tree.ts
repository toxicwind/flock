// Lazy drill-down rows: project under an agent, session under a project. Each
// expandable row fetches its children only when first opened (see `wireExpander`),
// so a collapsed tree costs nothing. The whole row is the toggle — not just the
// caret. Rows render `label` only, never the opaque `key` (raw project path /
// session id) that round-trips the follow-up query.

import type { ChildCard } from "./types.js";
import { el } from "./dom.js";
import { formatBill, formatPct, formatRelative } from "./format.js";

/** A drill-down row plus, for non-leaf rows, a loader for its children. */
export interface TreeNode {
  card: ChildCard;
  /** Absent on leaves (sessions). Present on rows that expand (projects). */
  loadChildren?: () => Promise<TreeNode[]>;
}

const SVG_NS = "http://www.w3.org/2000/svg";

/** Disclosure chevron; rotates 90° via CSS when its row is `aria-expanded`. */
export function caret(): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "12");
  svg.setAttribute("height", "12");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2.5");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("class", "caret-icon");
  const p = document.createElementNS(SVG_NS, "path");
  p.setAttribute("d", "M9 6l6 6-6 6");
  svg.appendChild(p);
  return svg;
}

function errorMessage(e: unknown): string {
  if (typeof e === "string") return e;
  if (e instanceof Error) return e.message;
  return "Failed to load.";
}

/** A collapsible region that animates open (grid 0fr → 1fr). Content mounts into `mount`. */
export function collapsible(): { region: HTMLElement; mount: HTMLElement } {
  const mount = el("div", { class: "tree-children-inner" });
  const region = el("div", { class: "tree-children" }, [mount]);
  return { region, mount };
}

/**
 * Turn `toggle` into a disclosure control for `region`: click (or Enter/Space,
 * since `toggle` is a <button>) expands/collapses it, filling `mount` on first
 * open. Children render as `treeRow`s at `depth`. Shared by the agent card (its
 * projects) and every project row (its sessions).
 */
export function wireExpander(
  toggle: HTMLElement,
  region: HTMLElement,
  mount: HTMLElement,
  loadNodes: () => Promise<TreeNode[]>,
  depth: number,
): void {
  let loaded = false;
  toggle.setAttribute("aria-expanded", "false");
  toggle.addEventListener("click", () => void run());

  async function run(): Promise<void> {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    region.classList.toggle("is-open", !open);
    if (open || loaded) return;
    loaded = true;
    mount.replaceChildren(hint("tree-loading", "Loading…"));
    try {
      const nodes = await loadNodes();
      mount.replaceChildren(
        ...(nodes.length
          ? nodes.map((n) => treeRow(n, depth))
          : [hint("tree-empty", "No sessions recorded yet.")]),
      );
    } catch (e) {
      loaded = false; // let a later click retry
      mount.replaceChildren(hint("tree-error", errorMessage(e)));
    }
  }
}

function hint(cls: string, text: string): HTMLElement {
  return el("div", { class: `tree-hint ${cls}` }, [text]);
}

/** The right-aligned metric cluster shared by every row: saved %, cost, recency. */
function metrics(card: ChildCard): HTMLElement {
  const hasData = card.has_savings_data;
  const pct = el("span", { class: hasData ? "tree-pct" : "tree-pct is-empty" }, [
    formatPct(card.saved_pct, hasData),
  ]);
  const bill = el("span", { class: "tree-bill" }, [formatBill(card.bill_micros)]);
  const when = el("span", { class: "tree-when" }, [formatRelative(card.last_event_ts)]);
  return el("span", { class: "tree-metrics" }, [pct, bill, when]);
}

/** One drill-down row; recurses through `wireExpander` for its own children. */
export function treeRow(node: TreeNode, depth: number): HTMLElement {
  const { card, loadChildren } = node;
  const label = el("span", { class: "tree-label" }, [card.label]);

  if (loadChildren) {
    const row = el(
      "button",
      {
        class: "tree-row tree-row-toggle",
        type: "button",
        "aria-label": `Toggle ${card.label}`,
      },
      [
        el("span", { class: "tree-caret" }, [caret()]),
        label,
        metrics(card),
      ],
    );
    const { region, mount } = collapsible();
    wireExpander(row, region, mount, loadChildren, depth + 1);
    return el("div", { class: "tree-node" }, [row, region]);
  }

  // Leaf (session): no caret, aligned under its project's label.
  const row = el("div", { class: "tree-row tree-row-leaf" }, [
    el("span", { class: "tree-caret tree-caret-empty", "aria-hidden": "true" }),
    label,
    metrics(card),
  ]);
  return el("div", { class: "tree-node" }, [row]);
}
