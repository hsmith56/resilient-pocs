#!/usr/bin/env python3
"""
Generate the tailored, easy-to-read assignment ruleset workflow HTML.

This restores the earlier semantic visualization style for the current
assignment_ruleset.py. The graph is intentionally human-oriented rather than a
literal rule-by-rule dump.

Usage:
    python validate_ruleset_workflow.py
    python validate_ruleset_workflow.py --ruleset assignment_ruleset.py --output assignment_ruleset_workflow.html

Note: the generic dynamic rule-by-rule generator was preserved as
validate_ruleset_workflow_dynamic.py.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List

SUPPORTED_OPERATORS = {
    "==", "!=", ">", ">=", "<", "<=", "in", "not_in", "missing", "not_missing"
}

HTML_TEMPLATE = Template(r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>$title</title>
  <style>
    :root {
      --bg: #f7f8fb; --card: #ffffff; --text: #1f2937; --muted: #6b7280;
      --border: #d8dee9; --ok: #0f766e; --warn: #b45309; --gap: #b91c1c; --info: #1d4ed8;
    }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.45; }
    header { position: sticky; top: 0; z-index: 10; background: rgba(247,248,251,.95); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); padding: .8rem 1rem; }
    header h1 { margin: 0 0 .25rem; font-size: 1.1rem; } header p { margin: 0; color: var(--muted); font-size: .9rem; }
    main { max-width: 1180px; margin: 0 auto; padding: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .75rem; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: .85rem; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
    .metric { font-size: 1.6rem; font-weight: 700; } .ok { color: var(--ok); } .warn { color: var(--warn); } .gap { color: var(--gap); } .info { color: var(--info); }
    details { margin-top: .75rem; } summary { cursor: pointer; font-weight: 650; } ul { margin: .5rem 0 0; padding-left: 1.2rem; } li { margin: .25rem 0; }
    .graph-card { margin-top: 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: .5rem; overflow-x: auto; cursor: zoom-in; }
    .graph-card:hover { border-color: #60a5fa; }
    .graph-hint { display: flex; justify-content: space-between; align-items: center; gap: .75rem; padding: .25rem .35rem .65rem; color: var(--muted); font-size: .9rem; }
    .open-graph-button, .modal-button { border: 1px solid var(--border); border-radius: 999px; background: #fff; color: var(--text); padding: .35rem .7rem; font-weight: 650; cursor: pointer; }
    .open-graph-button:hover, .modal-button:hover { background: #eff6ff; border-color: #60a5fa; }
    .mermaid { min-width: 760px; max-height: none; }
    body.graph-modal-open { overflow: hidden; }
    .graph-modal { position: fixed; inset: 0; z-index: 1000; display: none; grid-template-rows: auto 1fr; background: rgba(15,23,42,.92); }
    .graph-modal.open { display: grid; }
    .graph-modal-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .75rem; padding: .7rem .9rem; color: #e5e7eb; border-bottom: 1px solid rgba(226,232,240,.18); }
    .graph-modal-toolbar strong { color: #fff; } .graph-modal-help { color: #cbd5e1; font-size: .9rem; } .graph-modal-controls { display: flex; gap: .5rem; align-items: center; }
    .modal-button { background: #1e293b; color: #e5e7eb; border-color: #475569; } .modal-button:hover { background: #334155; border-color: #93c5fd; }
    .graph-viewport { position: relative; overflow: hidden; background: radial-gradient(circle at 1px 1px, rgba(148,163,184,.26) 1px, transparent 0), #0f172a; background-size: 22px 22px; cursor: grab; touch-action: none; user-select: none; }
    .graph-viewport.dragging { cursor: grabbing; }
    .graph-canvas { transform-origin: 0 0; will-change: transform; display: inline-block; padding: 32px; }
    .graph-canvas svg { display: block; max-width: none !important; background: #fff; border-radius: 12px; box-shadow: 0 18px 60px rgba(0,0,0,.35); }
    .graph-error { max-width: 640px; margin: 40px; padding: 1rem; border-radius: 12px; background: #fef2f2; color: #7f1d1d; border: 1px solid #ef4444; box-shadow: 0 18px 60px rgba(0,0,0,.35); }
    pre { overflow: auto; background: #0f172a; color: #e5e7eb; padding: .75rem; border-radius: 10px; font-size: .82rem; }
    table { width: 100%; border-collapse: collapse; font-size: .9rem; } th, td { border-bottom: 1px solid var(--border); text-align: left; padding: .45rem; vertical-align: top; } th { color: var(--muted); font-weight: 650; }
    .pill { display: inline-block; padding: .1rem .45rem; border-radius: 999px; background: #eef2ff; color: #3730a3; font-size: .78rem; }
    .context-card h2 { margin: 0 0 .45rem; font-size: 1.05rem; }
    .context-card h3 { margin: .2rem 0 .25rem; font-size: .95rem; }
    .context-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); gap: .75rem; margin-top: .65rem; }
    .context-item { border: 1px solid var(--border); border-radius: 10px; padding: .7rem; background: #fbfdff; }
    .context-item p { margin: .25rem 0 0; color: var(--muted); font-size: .9rem; }
    .context-card .hint { color: var(--info); font-weight: 650; }
    .node-has-help { cursor: help; }
    .node-tooltip { position: fixed; z-index: 2000; display: none; max-width: 340px; padding: .7rem .8rem; border-radius: 10px; background: #111827; color: #f9fafb; font-size: .88rem; line-height: 1.35; box-shadow: 0 18px 45px rgba(0,0,0,.28); pointer-events: none; border: 1px solid rgba(255,255,255,.18); }
    .node-tooltip.visible { display: block; }
    .node-tooltip strong { display: block; margin-bottom: .25rem; color: #bfdbfe; font-size: .82rem; text-transform: uppercase; letter-spacing: .02em; }
  </style>
</head>
<body>
  <header><h1>$title</h1><p>Tailored semantic workflow for <code>$ruleset_path</code>. Red nodes with question marks are undefined/gap paths.</p></header>
  <main>
    <section class="grid">
      <div class="card"><div class="metric $status_class">$status_label</div><div>Validation status</div></div>
      <div class="card"><div class="metric">$rule_count</div><div>Rules loaded</div></div>
      <div class="card"><div class="metric gap">$gap_count</div><div>Gap branches shown</div></div>
      <div class="card"><div class="metric warn">$warning_count</div><div>Warnings</div></div>
    </section>
    <section class="card" style="margin-top:1rem;"><h2 style="margin-top:0;font-size:1rem;">Validation findings</h2>$findings_html<details><summary>Rule priority table</summary>$priority_table</details></section>
    <section class="card context-card" id="workflow-context" style="margin-top:1rem;">
      <h2>Plain-English guide to holds and locks</h2>
      <p><span class="hint">Hover over criteria and lock nodes in the graph</span> to see simple explanations. A hold is the business reason ownership should stay put; a lock is the router's stored protection that prevents later automatic owner changes from bouncing the case away.</p>
      <div class="context-grid">
        <div class="context-item" id="criteria-4-guide"><h3>Criteria 4 GF CIHT hold</h3><p>When CBD is GF, impact is 0-2, and the caused-by/type condition matches, the router keeps the owner with CIHT and automatically sets a condition-based owner lock. It breaks automatically when impact becomes 3-5, CBD changes away from GF, or the original caused-by/type condition stops matching.</p></div>
        <div class="context-item" id="criteria-5-guide"><h3>Criteria 5 CIHT/WMA manual transfer lock</h3><p>When the router sees a manual transfer between CIHT and WMA while impact is 0-2, it preserves the new owner and automatically sets a manual-transfer lock for the case lifecycle. It breaks automatically if impact becomes 3-5 so escalation routing can apply.</p></div>
        <div class="context-item" id="manual-lock-guide"><h3>Manual / incident-lifetime locks</h3><p>These locks protect the current owner from automatic owner changes. They are not released by normal rule evaluation; an authorized user/admin must clear the lock fields or change the assignment mode/process that set them.</p></div>
        <div class="context-item" id="assignment-mode-guide"><h3>Assignment mode skip</h3><p>If assignment mode is Manual Override or Locked, the router skips automatic routing entirely and preserves current owner, members, workspace, and lock state. Clear assignment mode to allow automatic routing again.</p></div>
        <div class="context-item" id="criteria-6-guide"><h3>Criteria 6 impact 0 / missing CBD routing</h3><p>In active phases, impact 0 routes to CIHT by default. GWM US remains the exception and routes to DISO-GWM US. If CBD is missing/unknown, owner routes to CIHT. Closed/completed phases still preserve current assignment.</p></div>
      </div>
    </section>
    <section class="graph-card" id="graphCard"><div class="graph-hint"><span>Click the workflow graph to open an interactive view. Mouse wheel zooms, drag pans, Escape closes. Hover criteria/lock nodes for plain-English help.</span><button type="button" class="open-graph-button" id="openGraphButton">Open interactive graph</button></div><div class="mermaid" id="workflowMermaid">$mermaid_graph</div></section>
    <details class="card"><summary>Raw Mermaid source</summary><pre>$mermaid_source</pre></details>
    <details class="card"><summary>Raw validation JSON</summary><pre>$validation_json</pre></details>
  </main>
  <div class="graph-modal" id="graphModal" aria-hidden="true" role="dialog" aria-label="Interactive workflow graph"><div class="graph-modal-toolbar"><div><strong>Interactive workflow graph</strong><div class="graph-modal-help">Wheel/trackpad to zoom, drag to pan, double-click to reset, Escape to close.</div></div><div class="graph-modal-controls"><button type="button" class="modal-button" id="zoomOutButton">−</button><button type="button" class="modal-button" id="zoomResetButton">Reset</button><button type="button" class="modal-button" id="zoomInButton">+</button><button type="button" class="modal-button" id="closeGraphButton">Close Esc</button></div></div><div class="graph-viewport" id="graphViewport"><div class="graph-canvas" id="graphCanvas"></div></div></div>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ startOnLoad:false, securityLevel:'loose', flowchart:{ htmlLabels:true, curve:'basis', nodeSpacing:28, rankSpacing:42 }, theme:'base', themeVariables:{ fontFamily:'Inter, ui-sans-serif, system-ui, sans-serif', primaryColor:'#eff6ff', primaryBorderColor:'#60a5fa', primaryTextColor:'#1f2937', lineColor:'#64748b', tertiaryColor:'#ffffff' }});
    await mermaid.run();
    const workflowDefinition = $workflow_json;
    let renderCounter = 0, scale = 1, translateX = 0, translateY = 0, isDragging = false, lastPointerX = 0, lastPointerY = 0;
    const graphCard = document.getElementById('graphCard'), openGraphButton = document.getElementById('openGraphButton'), modal = document.getElementById('graphModal'), viewport = document.getElementById('graphViewport'), canvas = document.getElementById('graphCanvas'), closeGraphButton = document.getElementById('closeGraphButton'), zoomInButton = document.getElementById('zoomInButton'), zoomOutButton = document.getElementById('zoomOutButton'), zoomResetButton = document.getElementById('zoomResetButton');
    const nodeHelp = [
      { text: 'Assignment mode', title: 'Assignment mode skip', tip: 'Manual Override or Locked means the router skips automatic routing and preserves the current assignment. Clear assignment_mode to let rules run again.' },
      { text: 'Criteria 5', title: 'Criteria 5 manual-transfer lock', tip: 'Protects manual transfers between CIHT and WMA while impact is 0-2. The router sets a manual_transfer owner lock so later lifecycle routing does not bounce the owner back. Impact 3-5 releases this lock.' },
      { text: 'manual_transfer lock', title: 'Manual-transfer lock', tip: 'Set automatically after a CIHT/WMA manual transfer. It keeps the current owner while impact is 0-2 and releases when impact becomes 3-5.' },
      { text: 'Criteria 4', title: 'Criteria 4 GF CIHT hold', tip: 'The GF CIHT hold. If CBD is GF, impact is 0-2, and caused-by/type matches, the router keeps owner as CIHT and sets a condition_based lock.' },
      { text: 'condition lock', title: 'Condition-based lock', tip: 'Kept only while the rule that created it still matches. It releases when CBD changes away from GF, impact becomes 3-5, or the caused-by/type condition stops matching.' },
      { text: 'condition_based lock', title: 'Condition-based lock', tip: 'Kept only while the rule that created it still matches. It releases when CBD changes away from GF, impact becomes 3-5, or the caused-by/type condition stops matching.' },
      { text: 'manual lock', title: 'Manual owner lock', tip: 'Protects the owner from automatic owner changes until an authorized user/admin explicitly clears the lock.' },
      { text: 'incident lifetime lock', title: 'Incident-lifetime lock', tip: 'Protects the owner for the life of the incident unless an authorized user/admin explicitly clears it.' },
      { text: 'Criteria 2', title: 'Criteria 2 routing', tip: 'Handles Response and Recovery ownership and impact escalation. Impact 3-5 routes to the CBD owner and adds CIHT as a member. Impact 1-2 uses the configured business-owner or CIHT rules.' },
      { text: 'Criteria 1', title: 'Criteria 1 Triage fallback', tip: 'Low-impact Triage routes GWM US to its owner and all other CBDs to CIHT unless another higher-priority rule matches.' },
      { text: 'Criteria 6', title: 'Criteria 6 impact 0 / missing CBD routing', tip: 'In active phases, impact 0 routes to CIHT by default. GWM US is the exception and routes to DISO-GWM US. If CBD is missing/unknown, owner routes to CIHT. Closed/completed phases still preserve current assignment.' }
    ];
    const tooltip = document.createElement('div');
    tooltip.className = 'node-tooltip';
    tooltip.setAttribute('role', 'tooltip');
    document.body.appendChild(tooltip);
    const tooltipBoundNodes = new WeakSet();
    function moveTooltip(event){ const pad = 14, margin = 12; let x = event.clientX + pad, y = event.clientY + pad; const rect = tooltip.getBoundingClientRect(); if (x + rect.width + margin > window.innerWidth) x = event.clientX - rect.width - pad; if (y + rect.height + margin > window.innerHeight) y = event.clientY - rect.height - pad; tooltip.style.left = Math.max(margin, x) + 'px'; tooltip.style.top = Math.max(margin, y) + 'px'; }
    function showTooltip(help, event){ tooltip.innerHTML = '<strong>' + help.title + '</strong>' + help.tip; tooltip.classList.add('visible'); moveTooltip(event); }
    function hideTooltip(){ tooltip.classList.remove('visible'); }
    function addNodeTooltips(root=document){ const nodes = root.querySelectorAll ? root.querySelectorAll('g.node') : []; nodes.forEach(node => { const label = (node.textContent || '').replace(/\s+/g, ' ').trim(); const help = nodeHelp.find(item => label.includes(item.text)); if (!help) return; node.classList.add('node-has-help'); node.querySelectorAll('title').forEach(t => t.remove()); if (tooltipBoundNodes.has(node)) return; tooltipBoundNodes.add(node); node.addEventListener('mouseenter', event => showTooltip(help, event)); node.addEventListener('mousemove', moveTooltip); node.addEventListener('mouseleave', hideTooltip); node.addEventListener('click', hideTooltip); }); }
    addNodeTooltips(document);
    function clamp(v,min,max){ return Math.min(max, Math.max(min, v)); }
    function applyTransform(){ canvas.style.transform = 'translate(' + translateX + 'px, ' + translateY + 'px) scale(' + scale + ')'; }
    function resetView(){ scale = 0.85; translateX = 24; translateY = 24; applyTransform(); }
    function zoomAt(clientX, clientY, factor){ const rect = viewport.getBoundingClientRect(), x = clientX - rect.left, y = clientY - rect.top, oldScale = scale, newScale = clamp(scale * factor, .18, 5); translateX = x - ((x - translateX) / oldScale) * newScale; translateY = y - ((y - translateY) / oldScale) * newScale; scale = newScale; applyTransform(); }
    function showModal(){ modal.classList.add('open'); modal.setAttribute('aria-hidden','false'); document.body.classList.add('graph-modal-open'); resetView(); }
    function sizeModalSvg(svg){ const vb = svg.viewBox && svg.viewBox.baseVal, box = svg.getBBox ? svg.getBBox() : null, w = Math.max(900, Math.ceil((vb && vb.width) || (box && box.width) || svg.clientWidth || 1200)), h = Math.max(700, Math.ceil((vb && vb.height) || (box && box.height) || svg.clientHeight || 1600)); svg.setAttribute('width', String(w)); svg.setAttribute('height', String(h)); svg.style.width = w + 'px'; svg.style.height = h + 'px'; svg.style.maxWidth = 'none'; svg.style.display = 'block'; }
    async function openGraph(){ canvas.innerHTML = ''; try { const rendered = await mermaid.render('interactiveGraphSvg' + (++renderCounter), workflowDefinition); canvas.innerHTML = rendered.svg; if (rendered.bindFunctions) rendered.bindFunctions(canvas); addNodeTooltips(canvas); const svg = canvas.querySelector('svg'); if (svg) sizeModalSvg(svg); showModal(); return; } catch(error) { console.warn('Direct Mermaid modal render failed; falling back to cloned SVG.', error); } const sourceSvg = document.querySelector('#workflowMermaid svg') || document.querySelector('.mermaid svg'); if (!sourceSvg) { canvas.innerHTML = '<div class="graph-error"><strong>Graph is not available.</strong><br/>Mermaid could not render the graph and no rendered SVG was found. Check browser console/network access.</div>'; showModal(); return; } const clone = sourceSvg.cloneNode(true); sizeModalSvg(clone); canvas.appendChild(clone); addNodeTooltips(canvas); showModal(); }
    function closeGraph(){ modal.classList.remove('open'); modal.setAttribute('aria-hidden','true'); document.body.classList.remove('graph-modal-open'); isDragging = false; viewport.classList.remove('dragging'); }
    graphCard.addEventListener('click', () => openGraph()); openGraphButton.addEventListener('click', e => { e.stopPropagation(); openGraph(); }); closeGraphButton.addEventListener('click', closeGraph);
    function zoomAtCenter(factor){ const rect = viewport.getBoundingClientRect(); zoomAt(rect.left + rect.width/2, rect.top + rect.height/2, factor); }
    zoomResetButton.addEventListener('click', resetView); zoomInButton.addEventListener('click', () => zoomAtCenter(1.25)); zoomOutButton.addEventListener('click', () => zoomAtCenter(.8));
    viewport.addEventListener('wheel', e => { e.preventDefault(); zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.12 : .89); }, { passive:false });
    viewport.addEventListener('pointerdown', e => { isDragging = true; lastPointerX = e.clientX; lastPointerY = e.clientY; viewport.setPointerCapture(e.pointerId); viewport.classList.add('dragging'); });
    viewport.addEventListener('pointermove', e => { if (!isDragging) return; translateX += e.clientX - lastPointerX; translateY += e.clientY - lastPointerY; lastPointerX = e.clientX; lastPointerY = e.clientY; applyTransform(); });
    function endDrag(e){ isDragging = false; viewport.classList.remove('dragging'); if (e.pointerId !== undefined && viewport.hasPointerCapture(e.pointerId)) viewport.releasePointerCapture(e.pointerId); }
    viewport.addEventListener('pointerup', endDrag); viewport.addEventListener('pointercancel', endDrag); viewport.addEventListener('dblclick', resetView); document.addEventListener('keydown', e => { if (e.key === 'Escape' && modal.classList.contains('open')) closeGraph(); });
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


def validate_ruleset(module: Any) -> Dict[str, Any]:
    rules = list(getattr(module, "ROUTING_RULES", []))
    findings: List[Dict[str, str]] = []
    if not rules:
        findings.append({"level": "error", "message": "ROUTING_RULES is missing or empty."})
    names = [rule.get("name") for rule in rules if isinstance(rule, dict)]
    for name in sorted({name for name in names if name and names.count(name) > 1}):
        findings.append({"level": "error", "message": f"Duplicate rule name: {name!r}."})
    for rule in rules:
        if not isinstance(rule, dict):
            findings.append({"level": "error", "message": "Rule is not a dictionary."})
            continue
        if not isinstance(rule.get("priority"), int):
            findings.append({"level": "error", "message": f"Rule {rule.get('name')!r} has a non-integer priority."})
        for field, condition in rule.get("conditions", {}).items():
            if isinstance(condition, dict) and condition.get("operator") not in SUPPORTED_OPERATORS:
                findings.append({"level": "error", "message": f"Rule {rule.get('name')!r} has unsupported operator {condition.get('operator')!r} on {field!r}."})
    gaps = [
        "Response and Recovery CBD values outside AM/P&C/GWM/GWM WMI/GF/IB at impact 1-2 are not explicitly routed.",
        "Exact completed/closed phase names are not defined; non-active phases preserve current assignment.",
        "Field value case normalization is not defined; current routing uses exact matching.",
        "Criteria 5 manual transfer is inferred from router state rather than true event history.",
        "Criteria 5 vs impact_rating >= 3 precedence is assumed: impact_rating 3-5 overrides manual transfer.",
    ]
    for gap in gaps:
        findings.append({"level": "gap", "message": gap})
    return {"rules": rules, "findings": findings, "gap_count": len(gaps)}


def make_mermaid(module: Any) -> str:
    business_map = getattr(module, "CBD_BUSINESS_OWNER_MAP", {})
    business_lines = "<br/>".join(f"{str(k).replace('&', 'and')} → {str(v).replace('&', 'and')}" for k, v in business_map.items()) or "AM/P&C/GWM mappings"
    return f"""flowchart TD
    classDef start fill:#ecfeff,stroke:#0891b2,color:#164e63,stroke-width:1px;
    classDef decision fill:#fff7ed,stroke:#f97316,color:#7c2d12,stroke-width:1px;
    classDef action fill:#ecfdf5,stroke:#10b981,color:#064e3b,stroke-width:1px;
    classDef gap fill:#fef2f2,stroke:#ef4444,color:#7f1d1d,stroke-width:2px;
    classDef skip fill:#f8fafc,stroke:#94a3b8,color:#334155,stroke-width:1px;
    classDef lock fill:#eef2ff,stroke:#6366f1,color:#312e81,stroke-width:1px;

    Start([Incident evaluated]):::start --> AssignmentMode{{assignment_mode is Manual Override or Locked?}}:::decision
    AssignmentMode -- Yes --> SkipAuto[Skip automatic routing<br/>preserve current assignment]:::skip
    AssignmentMode -- No --> HasLock{{Existing owner lock?}}:::decision

    HasLock -- No --> ManualTransferCheck{{Criteria 5 manual transfer owner<br/>DISO-CIHT or DISO-WMA<br/>and impact_rating in 0-2?}}:::decision
    HasLock -- Yes --> LockType{{Lock type?}}:::decision
    LockType -- manual --> KeepManual[Keep manual lock<br/>owner protected]:::lock
    LockType -- incident_lifetime --> KeepLifetime[Keep incident lifetime lock<br/>owner protected]:::lock
    LockType -- condition_based --> ConditionStillMatches{{Original lock rule still matches?}}:::decision
    LockType -- manual_transfer --> ManualLockHigh{{impact_rating >= 3<br/>values 3-5?}}:::decision
    ConditionStillMatches -- Yes --> KeepCondition[Keep condition lock<br/>owner protected]:::lock
    ConditionStillMatches -- No --> ReleaseCondition[Release condition lock<br/>re-evaluate routing]:::lock
    ManualLockHigh -- Yes: 3-5 --> ReleaseManualTransfer[Release manual_transfer lock<br/>allow impact_rating >= 3 routing]:::lock
    ManualLockHigh -- No: 0-2 --> KeepManualTransfer[Keep manual_transfer lock<br/>owner protected]:::lock
    ReleaseCondition --> ManualTransferCheck
    ReleaseManualTransfer --> ManualTransferCheck
    KeepManual --> LockedPath[Evaluate matching rules<br/>but owner cannot change while locked]:::lock
    KeepLifetime --> LockedPath
    KeepCondition --> LockedPath
    KeepManualTransfer --> LockedPath
    LockedPath --> PhaseCheck{{Phase?}}:::decision

    ManualTransferCheck -- Yes: owner pair and 0-2 --> Criteria5[Criteria 5<br/>owner = current manual transfer owner<br/>DISO-CIHT or DISO-WMA<br/>set manual_transfer lock]:::action
    ManualTransferCheck -- No: condition not satisfied --> PhaseCheck

    PhaseCheck -- Triage --> TriageImpact{{Triage: impact_rating >= 3<br/>values 3-5?}}:::decision
    PhaseCheck -- Response and Recovery --> RRImpact{{Response and Recovery: impact_rating >= 3<br/>values 3-5?}}:::decision
    PhaseCheck -- Other phase --> OtherPhase[No rule match<br/>preserve current owner/members<br/>❓ completed/closed phase names not explicit]:::gap

    TriageImpact -- Yes: 3-5 --> TriageCBDPresent{{CBD present?}}:::decision
    TriageCBDPresent -- No --> TriageMissingCBD[Criteria 6<br/>missing CBD<br/>owner = DISO-CIHT<br/>members unchanged]:::action
    TriageCBDPresent -- Yes --> TriageHigh[Criteria 2 impact_rating >= 3<br/>owner = DISO-cbd<br/>members = existing + CIHT]:::action
    TriageImpact -- No: 0-2 --> TriageGFHold{{CBD == GF<br/>and Criteria 4 hold?}}:::decision
    TriageGFHold -- causedby rule --> TriageC4A[Criteria 4<br/>causedby IT systems or Other third party<br/>owner = DISO-CIHT<br/>set condition_based lock]:::action
    TriageGFHold -- causedby/type rule --> TriageC4B[Criteria 4<br/>causedby Employee or Other third party<br/>type cyber attack or cyber incident<br/>owner = DISO-CIHT<br/>set condition_based lock]:::action
    TriageGFHold -- No --> TriageGWMUS{{cbd == GWM US?}}:::decision
    TriageGWMUS -- Yes --> TriageGWMUSOwner[Criteria 1<br/>owner = DISO-GWM US]:::action
    TriageGWMUS -- No --> TriageDefault[Criteria 1 fallback<br/>owner = DISO-CIHT]:::action

    RRImpact -- Yes: 3-5 --> RRCBDPresent{{CBD present?}}:::decision
    RRCBDPresent -- No --> RRMissingCBD[Criteria 6<br/>missing CBD<br/>owner = DISO-CIHT<br/>members unchanged]:::action
    RRCBDPresent -- Yes --> RRHigh[Criteria 2 impact_rating >= 3<br/>owner = DISO-cbd<br/>members = existing + CIHT]:::action
    RRImpact -- No: 0-2 --> RRGFHold{{CBD == GF<br/>and Criteria 4 hold?}}:::decision
    RRGFHold -- causedby rule --> RRC4A[Criteria 4<br/>causedby IT systems or Other third party<br/>owner = DISO-CIHT<br/>set condition_based lock]:::action
    RRGFHold -- causedby/type rule --> RRC4B[Criteria 4<br/>causedby Employee or Other third party<br/>type cyber attack or cyber incident<br/>owner = DISO-CIHT<br/>set condition_based lock]:::action
    RRGFHold -- No --> RRBusiness{{CBD in AM/P&C/GWM/GWM WMI<br/>and impact_rating in 1-2?}}:::decision
    RRBusiness -- Yes: condition satisfied --> RRBusinessOwner[Criteria 2<br/>{business_lines}<br/>members = existing + CIHT]:::action
    RRBusiness -- No: condition not satisfied --> RRGFIB{{CBD is GF or IB<br/>and impact_rating in 1-2?}}:::decision
    RRGFIB -- Yes: condition satisfied --> RRCIHT[Criteria 2<br/>owner = DISO-CIHT<br/>members unchanged]:::action
    RRGFIB -- No: condition not satisfied --> RRImpactZero{{impact_rating == 0?}}:::decision
    RRImpactZero -- Yes: impact 0 --> RRGWMUSZero{{CBD == GWM US?}}:::decision
    RRGWMUSZero -- Yes --> RRGWMUSZeroOwner[Criteria 6<br/>impact 0 exception<br/>owner = DISO-GWM US<br/>members unchanged]:::action
    RRGWMUSZero -- No --> RRCIHTZero[Criteria 6<br/>impact 0 default<br/>owner = DISO-CIHT<br/>members unchanged]:::action
    RRImpactZero -- No: impact 1-2 but CBD not routed --> RRNoMatch[❓ Gap / no matching rule<br/>preserve current owner/members]:::gap

    Criteria5 --> End([Apply changes and write audit]):::start
    SkipAuto --> End
    OtherPhase --> End
    TriageMissingCBD --> End
    TriageHigh --> End
    TriageC4A --> End
    TriageC4B --> End
    TriageGWMUSOwner --> End
    TriageDefault --> End
    RRMissingCBD --> End
    RRHigh --> End
    RRC4A --> End
    RRC4B --> End
    RRBusinessOwner --> End
    RRCIHT --> End
    RRGWMUSZeroOwner --> End
    RRCIHTZero --> End
    RRNoMatch --> End"""


def findings_html(findings: List[Dict[str, str]]) -> str:
    grouped: Dict[str, List[str]] = {"error": [], "warning": [], "gap": [], "info": []}
    for finding in findings:
        grouped.setdefault(finding["level"], []).append(finding["message"])
    if not findings:
        return "<p class='ok'>No findings.</p>"
    labels = {"error": ("gap", "Errors"), "warning": ("warn", "Warnings"), "gap": ("gap", "Undefined/gap branches"), "info": ("info", "Info")}
    parts: List[str] = []
    for level in ["error", "warning", "gap", "info"]:
        messages = grouped.get(level, [])
        if not messages:
            continue
        css, label = labels[level]
        parts.append(f"<details {'open' if level in {'error', 'gap'} else ''}><summary class='{css}'>{label} ({len(messages)})</summary><ul>")
        parts.extend(f"<li>{html.escape(message)}</li>" for message in messages)
        parts.append("</ul></details>")
    return "\n".join(parts)


def priority_table(rules: List[Dict[str, Any]]) -> str:
    rows = ["<table><thead><tr><th>Priority</th><th>Phase</th><th>Name</th><th>Conditions</th><th>Assignment</th></tr></thead><tbody>"]
    for rule in sorted(rules, key=lambda r: r.get("priority", 0), reverse=True):
        rows.append("<tr>" + f"<td><span class='pill'>{html.escape(str(rule.get('priority')))}</span></td>" + f"<td>{html.escape(str(rule.get('phase', 'Any')))}</td>" + f"<td>{html.escape(str(rule.get('name')))}</td>" + f"<td><code>{html.escape(json.dumps(rule.get('conditions', {}), default=str))}</code></td>" + f"<td><code>{html.escape(json.dumps(rule.get('assignment', {}), default=str))}</code></td>" + "</tr>")
    rows.append("</tbody></table>")
    return "\n".join(rows)


def write_html(ruleset_path: Path, output_path: Path, validation: Dict[str, Any], graph: str) -> None:
    errors = sum(1 for f in validation["findings"] if f["level"] == "error")
    warnings = sum(1 for f in validation["findings"] if f["level"] == "warning")
    output_path.write_text(HTML_TEMPLATE.substitute(
        title="Assignment Ruleset Workflow Validation",
        ruleset_path=html.escape(str(ruleset_path)),
        status_class="ok" if errors == 0 else "gap",
        status_label="PASS" if errors == 0 else "FAIL",
        rule_count=str(len(validation["rules"])),
        gap_count=str(validation["gap_count"]),
        warning_count=str(warnings),
        findings_html=findings_html(validation["findings"]),
        priority_table=priority_table(validation["rules"]),
        mermaid_graph=html.escape(graph),
        mermaid_source=html.escape(graph),
        validation_json=html.escape(json.dumps(validation, indent=2, default=str)),
        workflow_json=json.dumps(graph),
    ), encoding="utf-8")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate the tailored assignment ruleset workflow HTML.")
    parser.add_argument("ruleset_positional", nargs="?", help="Optional ruleset path")
    parser.add_argument("--ruleset", help="Ruleset path. Defaults to assignment_ruleset.py")
    parser.add_argument("--output", default="assignment_ruleset_workflow.html", help="Output HTML path")
    args = parser.parse_args(argv)
    ruleset_path = Path(args.ruleset or args.ruleset_positional or "assignment_ruleset.py").resolve()
    output_path = Path(args.output).resolve()
    module = load_ruleset(ruleset_path)
    validation = validate_ruleset(module)
    graph = make_mermaid(module)
    write_html(ruleset_path, output_path, validation, graph)
    errors = sum(1 for f in validation["findings"] if f["level"] == "error")
    warnings = sum(1 for f in validation["findings"] if f["level"] == "warning")
    print(f"Wrote workflow HTML: {output_path}")
    print(f"Rules: {len(validation['rules'])}; errors: {errors}; warnings: {warnings}; gaps: {validation['gap_count']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
