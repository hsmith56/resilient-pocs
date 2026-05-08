#!/usr/bin/env python3
"""
Validate a Python ruleset file and generate an interactive HTML workflow graph.

The graph is generated dynamically from the provided module's ROUTING_RULES. It
is not tied to any specific business ruleset.

Usage:
    python validate_ruleset_workflow.py
    python validate_ruleset_workflow.py --ruleset assignment_ruleset.py --output workflow.html
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, List, Optional, Tuple

SUPPORTED_OPERATORS = {
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "not_in",
    "missing",
    "not_missing",
}

KNOWN_CONTEXT_FIELDS = {
    "id",
    "name",
    "phase",
    "severity",
    "impact_rating",
    "is_high_impact",
    "cbd",
    "causedby",
    "type",
    "manual_transfer_owner",
    "assignment_router_last_owner",
    "assignment_mode",
    "assignment_owner_locked",
    "assignment_owner_lock_type",
    "assignment_owner_lock_rule",
    "assignment_owner_lock_reason",
    "current_workspace",
    "current_owner",
    "current_members",
}

HTML_TEMPLATE = Template(r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>$title</title>
  <style>
    :root {
      --bg: #f7f8fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --border: #d8dee9;
      --ok: #0f766e;
      --warn: #b45309;
      --gap: #b91c1c;
      --info: #1d4ed8;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(247, 248, 251, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
      padding: 0.8rem 1rem;
    }
    header h1 { margin: 0 0 0.25rem; font-size: 1.1rem; }
    header p { margin: 0; color: var(--muted); font-size: 0.9rem; }
    main { max-width: 1180px; margin: 0 auto; padding: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.85rem;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .metric { font-size: 1.6rem; font-weight: 700; }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .gap { color: var(--gap); }
    .info { color: var(--info); }
    details { margin-top: 0.75rem; }
    summary { cursor: pointer; font-weight: 650; }
    ul { margin: 0.5rem 0 0; padding-left: 1.2rem; }
    li { margin: 0.25rem 0; }
    .graph-card {
      margin-top: 1rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.5rem;
      overflow-x: auto;
      cursor: zoom-in;
    }
    .graph-card:hover { border-color: #60a5fa; }
    .graph-hint {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.75rem;
      padding: 0.25rem 0.35rem 0.65rem;
      color: var(--muted);
      font-size: 0.9rem;
    }
    .open-graph-button, .modal-button {
      border: 1px solid var(--border);
      border-radius: 999px;
      background: #ffffff;
      color: var(--text);
      padding: 0.35rem 0.7rem;
      font-weight: 650;
      cursor: pointer;
    }
    .open-graph-button:hover, .modal-button:hover { background: #eff6ff; border-color: #60a5fa; }
    .mermaid { min-width: 760px; max-height: none; }
    body.graph-modal-open { overflow: hidden; }
    .graph-modal {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: none;
      grid-template-rows: auto 1fr;
      background: rgba(15, 23, 42, 0.92);
    }
    .graph-modal.open { display: grid; }
    .graph-modal-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.7rem 0.9rem;
      color: #e5e7eb;
      border-bottom: 1px solid rgba(226, 232, 240, 0.18);
    }
    .graph-modal-toolbar strong { color: #ffffff; }
    .graph-modal-help { color: #cbd5e1; font-size: 0.9rem; }
    .graph-modal-controls { display: flex; gap: 0.5rem; align-items: center; }
    .modal-button { background: #1e293b; color: #e5e7eb; border-color: #475569; }
    .modal-button:hover { background: #334155; border-color: #93c5fd; }
    .graph-viewport {
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(circle at 1px 1px, rgba(148, 163, 184, 0.26) 1px, transparent 0),
        #0f172a;
      background-size: 22px 22px;
      cursor: grab;
      touch-action: none;
      user-select: none;
    }
    .graph-viewport.dragging { cursor: grabbing; }
    .graph-canvas {
      transform-origin: 0 0;
      will-change: transform;
      display: inline-block;
      padding: 32px;
    }
    .graph-canvas svg {
      display: block;
      max-width: none !important;
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
    }
    .graph-error {
      max-width: 640px;
      margin: 40px;
      padding: 1rem;
      border-radius: 12px;
      background: #fef2f2;
      color: #7f1d1d;
      border: 1px solid #ef4444;
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
    }
    pre {
      overflow: auto;
      background: #0f172a;
      color: #e5e7eb;
      padding: 0.75rem;
      border-radius: 10px;
      font-size: 0.82rem;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { border-bottom: 1px solid var(--border); text-align: left; padding: 0.45rem; vertical-align: top; }
    th { color: var(--muted); font-weight: 650; }
    .pill { display: inline-block; padding: 0.1rem 0.45rem; border-radius: 999px; background: #eef2ff; color: #3730a3; font-size: 0.78rem; }
  </style>
</head>
<body>
  <header>
    <h1>$title</h1>
    <p>Generated dynamically from <code>$ruleset_path</code>. The graph follows the loaded ROUTING_RULES in priority order. Red nodes with question marks are possible undefined/no-match paths.</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><div class="metric $status_class">$status_label</div><div>Validation status</div></div>
      <div class="card"><div class="metric">$rule_count</div><div>Rules loaded</div></div>
      <div class="card"><div class="metric gap">$gap_count</div><div>Potential gaps</div></div>
      <div class="card"><div class="metric warn">$warning_count</div><div>Warnings</div></div>
    </section>

    <section class="card" style="margin-top: 1rem;">
      <h2 style="margin-top:0; font-size:1rem;">Validation findings</h2>
      $findings_html
      <details>
        <summary>Rule priority table</summary>
        $priority_table
      </details>
    </section>

    <section class="graph-card" id="graphCard" title="Click to open interactive zoom/pan view">
      <div class="graph-hint">
        <span>Click the workflow graph to open an interactive view. In interactive view: mouse wheel zooms, drag pans, Escape closes.</span>
        <button type="button" class="open-graph-button" id="openGraphButton">Open interactive graph</button>
      </div>
      <div class="mermaid" id="workflowMermaid">$mermaid_graph</div>
    </section>

    <details class="card">
      <summary>Raw Mermaid source</summary>
      <pre>$mermaid_source</pre>
    </details>

    <details class="card">
      <summary>Raw validation JSON</summary>
      <pre>$validation_json</pre>
    </details>
  </main>

  <div class="graph-modal" id="graphModal" aria-hidden="true" role="dialog" aria-label="Interactive workflow graph">
    <div class="graph-modal-toolbar">
      <div>
        <strong>Interactive workflow graph</strong>
        <div class="graph-modal-help">Wheel/trackpad to zoom, drag to pan, double-click to reset, Escape to close.</div>
      </div>
      <div class="graph-modal-controls">
        <button type="button" class="modal-button" id="zoomOutButton">−</button>
        <button type="button" class="modal-button" id="zoomResetButton">Reset</button>
        <button type="button" class="modal-button" id="zoomInButton">+</button>
        <button type="button" class="modal-button" id="closeGraphButton">Close Esc</button>
      </div>
    </div>
    <div class="graph-viewport" id="graphViewport">
      <div class="graph-canvas" id="graphCanvas"></div>
    </div>
  </div>

  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      flowchart: {
        htmlLabels: true,
        curve: 'basis',
        nodeSpacing: 28,
        rankSpacing: 42
      },
      theme: 'base',
      themeVariables: {
        fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
        primaryColor: '#eff6ff',
        primaryBorderColor: '#60a5fa',
        primaryTextColor: '#1f2937',
        lineColor: '#64748b',
        tertiaryColor: '#ffffff'
      }
    });

    await mermaid.run();

    const workflowDefinition = $workflow_json;
    let renderCounter = 0;

    const graphCard = document.getElementById('graphCard');
    const openGraphButton = document.getElementById('openGraphButton');
    const modal = document.getElementById('graphModal');
    const viewport = document.getElementById('graphViewport');
    const canvas = document.getElementById('graphCanvas');
    const closeGraphButton = document.getElementById('closeGraphButton');
    const zoomInButton = document.getElementById('zoomInButton');
    const zoomOutButton = document.getElementById('zoomOutButton');
    const zoomResetButton = document.getElementById('zoomResetButton');

    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let lastPointerX = 0;
    let lastPointerY = 0;

    function clamp(value, min, max) {
      return Math.min(max, Math.max(min, value));
    }

    function applyTransform() {
      canvas.style.transform = 'translate(' + translateX + 'px, ' + translateY + 'px) scale(' + scale + ')';
    }

    function resetView() {
      scale = 0.85;
      translateX = 24;
      translateY = 24;
      applyTransform();
    }

    function zoomAt(clientX, clientY, factor) {
      const rect = viewport.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      const oldScale = scale;
      const newScale = clamp(scale * factor, 0.18, 5);
      translateX = x - ((x - translateX) / oldScale) * newScale;
      translateY = y - ((y - translateY) / oldScale) * newScale;
      scale = newScale;
      applyTransform();
    }

    function showModal() {
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('graph-modal-open');
      resetView();
    }

    function sizeModalSvg(svgElement) {
      const viewBox = svgElement.viewBox && svgElement.viewBox.baseVal;
      const bbox = svgElement.getBBox ? svgElement.getBBox() : null;
      const width = Math.max(900, Math.ceil((viewBox && viewBox.width) || (bbox && bbox.width) || svgElement.clientWidth || 1200));
      const height = Math.max(700, Math.ceil((viewBox && viewBox.height) || (bbox && bbox.height) || svgElement.clientHeight || 1600));
      svgElement.setAttribute('width', String(width));
      svgElement.setAttribute('height', String(height));
      svgElement.style.width = width + 'px';
      svgElement.style.height = height + 'px';
      svgElement.style.maxWidth = 'none';
      svgElement.style.display = 'block';
    }

    async function openGraph() {
      canvas.innerHTML = '';
      try {
        const renderId = 'interactiveGraphSvg' + (++renderCounter);
        const rendered = await mermaid.render(renderId, workflowDefinition);
        canvas.innerHTML = rendered.svg;
        if (rendered.bindFunctions) rendered.bindFunctions(canvas);
        const modalSvg = canvas.querySelector('svg');
        if (modalSvg) sizeModalSvg(modalSvg);
        showModal();
        return;
      } catch (error) {
        console.warn('Direct Mermaid modal render failed; falling back to cloned SVG.', error);
      }

      const sourceSvg = document.querySelector('#workflowMermaid svg') || document.querySelector('.mermaid svg');
      if (!sourceSvg) {
        canvas.innerHTML = '<div class="graph-error"><strong>Graph is not available.</strong><br/>Mermaid could not render the graph and no rendered SVG was found. Check browser console/network access.</div>';
        showModal();
        return;
      }
      const clone = sourceSvg.cloneNode(true);
      sizeModalSvg(clone);
      canvas.appendChild(clone);
      showModal();
    }

    function closeGraph() {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('graph-modal-open');
      isDragging = false;
      viewport.classList.remove('dragging');
    }

    graphCard.addEventListener('click', () => openGraph());
    openGraphButton.addEventListener('click', (event) => {
      event.stopPropagation();
      openGraph();
    });
    closeGraphButton.addEventListener('click', closeGraph);

    function zoomAtCenter(factor) {
      const rect = viewport.getBoundingClientRect();
      zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, factor);
    }

    zoomResetButton.addEventListener('click', resetView);
    zoomInButton.addEventListener('click', () => zoomAtCenter(1.25));
    zoomOutButton.addEventListener('click', () => zoomAtCenter(0.8));

    viewport.addEventListener('wheel', (event) => {
      event.preventDefault();
      const factor = event.deltaY < 0 ? 1.12 : 0.89;
      zoomAt(event.clientX, event.clientY, factor);
    }, { passive: false });

    viewport.addEventListener('pointerdown', (event) => {
      isDragging = true;
      lastPointerX = event.clientX;
      lastPointerY = event.clientY;
      viewport.setPointerCapture(event.pointerId);
      viewport.classList.add('dragging');
    });

    viewport.addEventListener('pointermove', (event) => {
      if (!isDragging) return;
      translateX += event.clientX - lastPointerX;
      translateY += event.clientY - lastPointerY;
      lastPointerX = event.clientX;
      lastPointerY = event.clientY;
      applyTransform();
    });

    function endDrag(event) {
      isDragging = false;
      viewport.classList.remove('dragging');
      if (event.pointerId !== undefined && viewport.hasPointerCapture(event.pointerId)) {
        viewport.releasePointerCapture(event.pointerId);
      }
    }

    viewport.addEventListener('pointerup', endDrag);
    viewport.addEventListener('pointercancel', endDrag);
    viewport.addEventListener('dblclick', resetView);

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && modal.classList.contains('open')) closeGraph();
    });
  </script>
</body>
</html>
""")


def load_ruleset(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import ruleset from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def iter_conditions(rule: Dict[str, Any]) -> Iterable[Tuple[str, Any]]:
    conditions = rule.get("conditions", {})
    if isinstance(conditions, dict):
        for field_name, condition in conditions.items():
            yield field_name, condition


def condition_to_text(field_name: str, condition: Any) -> str:
    if isinstance(condition, dict):
        operator = condition.get("operator", "?")
        value = condition.get("value")
        if operator == "in":
            return f"{field_name} in {value!r}"
        if operator == "not_in":
            return f"{field_name} not in {value!r}"
        if operator == "missing":
            return f"{field_name} is missing"
        if operator == "not_missing":
            return f"{field_name} is present"
        return f"{field_name} {operator} {value!r}"
    if isinstance(condition, list):
        return f"{field_name} in {condition!r}"
    return f"{field_name} == {condition!r}"


def rule_condition_summary(rule: Dict[str, Any]) -> str:
    parts: List[str] = []
    if rule.get("phase"):
        parts.append(f"phase == {rule['phase']!r}")
    parts.extend(condition_to_text(field, cond) for field, cond in iter_conditions(rule))
    return " AND ".join(parts) if parts else "always matches"


def assignment_value_to_text(value: Any) -> str:
    if isinstance(value, dict):
        if "context" in value:
            return f"context[{value['context']!r}]"
        if "field" in value:
            pieces = [f"from field {value['field']!r}"]
            if value.get("map"):
                pieces.append(f"map {value['map']!r}")
            if value.get("default_template"):
                pieces.append(f"default {value['default_template']!r}")
            if value.get("missing_value") is not None:
                pieces.append(f"missing {value['missing_value']!r}")
            return "; ".join(pieces)
    return repr(value)


def rule_assignment_summary(rule: Dict[str, Any]) -> str:
    assignment = rule.get("assignment", {})
    pieces: List[str] = []
    if isinstance(assignment, dict):
        for key, value in assignment.items():
            pieces.append(f"{key} = {assignment_value_to_text(value)}")
    locks = rule.get("locks", {})
    if isinstance(locks, dict) and locks:
        pieces.append(f"locks = {locks!r}")
    return "\n".join(pieces) if pieces else "match only / no assignment"


def safe_node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


def mermaid_label(text: str, max_len: int = 260) -> str:
    text = re.sub(r"\s+", " ", text.replace("\n", " | ")).strip()
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    text = html.escape(text, quote=False)
    text = text.replace("|", "<br/>")
    text = text.replace('"', "'")
    return text


def mermaid_node(node_id: str, label: str, shape: str = "rect", css_class: str = "") -> str:
    safe_label = mermaid_label(label)
    if shape == "decision":
        line = f'    {node_id}{{"{safe_label}"}}'
    elif shape == "round":
        line = f'    {node_id}(["{safe_label}"])'
    else:
        line = f'    {node_id}["{safe_label}"]'
    if css_class:
        line += f":::{css_class}"
    return line


def sorted_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)


def validate_ruleset(module: Any) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []
    rules = list(getattr(module, "ROUTING_RULES", []))

    if not isinstance(rules, list) or not rules:
        findings.append({"level": "error", "message": "ROUTING_RULES must be a non-empty list."})
        return {"rules": [], "findings": findings, "gap_count": 0}

    names: List[Optional[str]] = []
    priorities: List[Any] = []
    phases = set()
    has_global_catch_all = False
    phase_has_catch_all = set()
    not_missing_fields: List[Tuple[str, Optional[str], str]] = []
    missing_handlers: set[Tuple[Optional[str], str]] = set()

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            findings.append({"level": "error", "message": f"Rule #{index + 1} is not a dict."})
            continue

        name = rule.get("name")
        priority = rule.get("priority")
        phase = rule.get("phase")
        conditions = rule.get("conditions", {})
        names.append(name)
        priorities.append(priority)

        if not name:
            findings.append({"level": "error", "message": f"Rule #{index + 1} is missing name."})
        if not isinstance(priority, int):
            findings.append({"level": "error", "message": f"Rule {name!r} has non-integer priority {priority!r}."})
        if phase is not None:
            if isinstance(phase, str):
                phases.add(phase)
            else:
                findings.append({"level": "error", "message": f"Rule {name!r} phase must be a string when present."})

        if not isinstance(conditions, dict):
            findings.append({"level": "error", "message": f"Rule {name!r} conditions must be a dict."})
            conditions = {}

        if not phase and not conditions:
            has_global_catch_all = True
        if phase and not conditions:
            phase_has_catch_all.add(phase)

        for field_name, condition in iter_conditions(rule):
            if field_name not in KNOWN_CONTEXT_FIELDS:
                findings.append({"level": "warning", "message": f"Rule {name!r} references unknown context field {field_name!r}."})
            if isinstance(condition, dict):
                operator = condition.get("operator")
                if operator not in SUPPORTED_OPERATORS:
                    findings.append({"level": "error", "message": f"Rule {name!r} uses unsupported operator {operator!r}."})
                if "value" not in condition and operator not in {"missing", "not_missing"}:
                    findings.append({"level": "warning", "message": f"Rule {name!r} condition {field_name!r} has no value key."})
                if operator == "not_missing":
                    not_missing_fields.append((field_name, phase, str(name)))
                if operator == "missing":
                    missing_handlers.add((phase, field_name))
            elif condition is getattr(module, "MISSING", object()):
                missing_handlers.add((phase, field_name))

        assignment = rule.get("assignment", {})
        if not isinstance(assignment, dict):
            findings.append({"level": "error", "message": f"Rule {name!r} assignment must be a dict."})
        else:
            owner = assignment.get("owner")
            if isinstance(owner, dict):
                if "context" not in owner and "field" not in owner:
                    findings.append({"level": "error", "message": f"Rule {name!r} has dynamic owner without context or field."})
                if "field" in owner and owner["field"] not in KNOWN_CONTEXT_FIELDS:
                    findings.append({"level": "warning", "message": f"Rule {name!r} owner references unknown field {owner['field']!r}."})

    duplicate_names = sorted({name for name in names if name and names.count(name) > 1})
    for name in duplicate_names:
        findings.append({"level": "error", "message": f"Duplicate rule name: {name!r}."})

    duplicate_priorities = sorted({p for p in priorities if isinstance(p, int) and priorities.count(p) > 1})
    for priority in duplicate_priorities:
        findings.append({"level": "info", "message": f"Priority {priority} is shared by multiple rules; verify those branches are intentionally non-conflicting or cumulative."})

    gap_count = 0
    if not has_global_catch_all:
        gap_count += 1
        findings.append({"level": "gap", "message": "No global catch-all rule exists; some incidents may match no rule."})

    for phase in sorted(phases):
        if phase not in phase_has_catch_all and not has_global_catch_all:
            gap_count += 1
            findings.append({"level": "gap", "message": f"Phase {phase!r} has no phase-level fallback rule; unmatched values in that phase can fall through."})

    for field_name, phase, rule_name in not_missing_fields:
        if (phase, field_name) not in missing_handlers and (None, field_name) not in missing_handlers:
            gap_count += 1
            scope = f"phase {phase!r}" if phase else "any phase"
            findings.append({"level": "gap", "message": f"Rule {rule_name!r} requires {field_name!r} to be present, but no explicit missing-value branch for {scope} was found."})

    return {"rules": rules, "findings": findings, "gap_count": gap_count}


def make_mermaid(module: Any, validation: Dict[str, Any]) -> str:
    rules = sorted_rules(validation["rules"])
    lines: List[str] = [
        "flowchart TD",
        "    classDef start fill:#ecfeff,stroke:#0891b2,color:#164e63,stroke-width:1px;",
        "    classDef decision fill:#fff7ed,stroke:#f97316,color:#7c2d12,stroke-width:1px;",
        "    classDef action fill:#ecfdf5,stroke:#10b981,color:#064e3b,stroke-width:1px;",
        "    classDef gap fill:#fef2f2,stroke:#ef4444,color:#7f1d1d,stroke-width:2px;",
        "    classDef skip fill:#f8fafc,stroke:#94a3b8,color:#334155,stroke-width:1px;",
        "    classDef info fill:#eef2ff,stroke:#6366f1,color:#312e81,stroke-width:1px;",
        mermaid_node("Start", "Incident evaluated", "round", "start"),
        mermaid_node("Pre", "Build incident context and evaluate rules in descending priority. Matching rules contribute assignment data; scalar fields keep the first/highest-priority value.", "rect", "info"),
        "    Start --> Pre",
    ]

    if not rules:
        lines.extend([
            mermaid_node("NoRules", "❓ No ROUTING_RULES found", "rect", "gap"),
            "    Pre --> NoRules",
        ])
        return "\n".join(lines)

    first_rule_id = safe_node_id("R", 1)
    lines.append(f"    Pre --> {first_rule_id}")

    for index, rule in enumerate(rules, start=1):
        rule_id = safe_node_id("R", index)
        yes_id = safe_node_id("Y", index)
        next_rule_id = safe_node_id("R", index + 1) if index < len(rules) else "Resolve"
        rule_label = (
            f"Rule {index}: {rule.get('name', '<unnamed>')}\n"
            f"priority: {rule.get('priority', '?')}\n"
            f"IF {rule_condition_summary(rule)}"
        )
        yes_label = f"Matched: {rule.get('name', '<unnamed>')}\n{rule_assignment_summary(rule)}"
        lines.append(mermaid_node(rule_id, rule_label, "decision", "decision"))
        lines.append(mermaid_node(yes_id, yes_label, "rect", "action"))
        lines.append(f"    {rule_id} -- yes --> {yes_id}")
        lines.append(f"    {yes_id} --> {next_rule_id}")
        lines.append(f"    {rule_id} -- no --> {next_rule_id}")

        for field_name, condition in iter_conditions(rule):
            if isinstance(condition, dict) and condition.get("operator") == "not_missing":
                gap_id = f"GapMissing{index}_{re.sub(r'[^A-Za-z0-9_]', '_', field_name)}"
                lines.append(mermaid_node(gap_id, f"❓ {field_name} missing for rule {rule.get('name', '<unnamed>')}\nNo explicit branch in this rule", "rect", "gap"))
                lines.append(f"    {rule_id} -. {field_name} missing .-> {gap_id}")

    lines.extend([
        mermaid_node("Resolve", "Any rules matched?", "decision", "decision"),
        mermaid_node("Apply", "Resolve final assignment deterministically\n- scalar fields: first/highest-priority match wins\n- members: cumulative when configured\n- locks/audit applied by router", "rect", "action"),
        mermaid_node("NoMatch", "❓ No matching rule\nCurrent assignment is preserved unless the router handles this separately", "rect", "gap"),
        mermaid_node("End", "End / write audit", "round", "start"),
        "    Resolve -- yes --> Apply",
        "    Resolve -- no --> NoMatch",
        "    Apply --> End",
        "    NoMatch --> End",
    ])
    return "\n".join(lines)


def findings_to_html(findings: List[Dict[str, str]]) -> str:
    if not findings:
        return "<p class='ok'>No validation findings.</p>"
    grouped: Dict[str, List[str]] = {"error": [], "warning": [], "gap": [], "info": []}
    for finding in findings:
        grouped.setdefault(finding["level"], []).append(finding["message"])
    labels = {
        "error": ("gap", "Errors"),
        "warning": ("warn", "Warnings"),
        "gap": ("gap", "Potential undefined/no-match branches"),
        "info": ("info", "Info"),
    }
    parts: List[str] = []
    for level in ["error", "warning", "gap", "info"]:
        messages = grouped.get(level, [])
        if not messages:
            continue
        css, label = labels[level]
        open_attr = " open" if level in {"error", "gap"} else ""
        parts.append(f"<details{open_attr}><summary class='{css}'>{label} ({len(messages)})</summary><ul>")
        parts.extend(f"<li>{html.escape(message)}</li>" for message in messages)
        parts.append("</ul></details>")
    return "\n".join(parts)


def priority_table_html(rules: List[Dict[str, Any]]) -> str:
    rows = ["<table><thead><tr><th>Priority</th><th>Phase</th><th>Name</th><th>Conditions</th><th>Assignment</th></tr></thead><tbody>"]
    for rule in sorted_rules(rules):
        conditions = html.escape(json.dumps(rule.get("conditions", {}), default=str))
        assignment = html.escape(json.dumps(rule.get("assignment", {}), default=str))
        rows.append(
            "<tr>"
            f"<td><span class='pill'>{html.escape(str(rule.get('priority')))}</span></td>"
            f"<td>{html.escape(str(rule.get('phase', 'Any')))}</td>"
            f"<td>{html.escape(str(rule.get('name')))}</td>"
            f"<td><code>{conditions}</code></td>"
            f"<td><code>{assignment}</code></td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "\n".join(rows)


def write_html(ruleset_path: Path, output_path: Path, validation: Dict[str, Any], mermaid_graph: str) -> None:
    findings = validation["findings"]
    error_count = sum(1 for f in findings if f["level"] == "error")
    warning_count = sum(1 for f in findings if f["level"] == "warning")
    status_label = "PASS" if error_count == 0 else "FAIL"
    status_class = "ok" if error_count == 0 else "gap"

    html_text = HTML_TEMPLATE.substitute(
        title="Assignment Ruleset Workflow Validation",
        ruleset_path=html.escape(str(ruleset_path)),
        status_label=status_label,
        status_class=status_class,
        rule_count=str(len(validation["rules"])),
        gap_count=str(validation["gap_count"]),
        warning_count=str(warning_count),
        findings_html=findings_to_html(findings),
        priority_table=priority_table_html(validation["rules"]),
        mermaid_graph=html.escape(mermaid_graph),
        mermaid_source=html.escape(mermaid_graph),
        validation_json=html.escape(json.dumps(validation, indent=2, default=str)),
        workflow_json=json.dumps(mermaid_graph),
    )
    output_path.write_text(html_text, encoding="utf-8")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate a Python ruleset and generate an interactive workflow HTML file.")
    parser.add_argument("ruleset_positional", nargs="?", help="Optional positional path to ruleset Python file.")
    parser.add_argument("--ruleset", help="Path to ruleset Python file. Defaults to assignment_ruleset.py.")
    parser.add_argument("--output", default="assignment_ruleset_workflow.html", help="Output HTML path.")
    args = parser.parse_args(argv)

    ruleset_arg = args.ruleset or args.ruleset_positional or "assignment_ruleset.py"
    ruleset_path = Path(ruleset_arg).resolve()
    output_path = Path(args.output).resolve()

    module = load_ruleset(ruleset_path)
    validation = validate_ruleset(module)
    mermaid_graph = make_mermaid(module, validation)
    write_html(ruleset_path, output_path, validation, mermaid_graph)

    errors = sum(1 for f in validation["findings"] if f["level"] == "error")
    warnings = sum(1 for f in validation["findings"] if f["level"] == "warning")
    print(f"Wrote workflow HTML: {output_path}")
    print(f"Rules: {len(validation['rules'])}; errors: {errors}; warnings: {warnings}; potential gaps: {validation['gap_count']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
