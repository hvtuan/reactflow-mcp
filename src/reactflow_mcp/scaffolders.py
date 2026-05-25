"""Code generators for custom React Flow nodes and edges.

Pure functions only — no MCP / IO concerns. The server module wires them
up as tools. Generated code targets `@xyflow/react` v12, TypeScript + React 18+.
"""

from __future__ import annotations

import re

VALID_POSITIONS = {"top", "right", "bottom", "left"}
VALID_HANDLE_KINDS = {"source", "target"}
VALID_STYLES = {"tailwind", "css-modules", "inline"}
VALID_PATH_TYPES = {"bezier", "smoothstep", "step", "straight", "simplebezier"}
PASCAL_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


def _to_pascal(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", name).strip()
    return "".join(p[:1].upper() + p[1:] for p in cleaned.split())


def _ts_type_for_default(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return "unknown"


# ───────────────────────── node scaffolder ─────────────────────────


def scaffold_custom_node(
    *,
    name: str,
    data_fields: list[dict] | None = None,
    handles: list[dict] | None = None,
    editable: bool = False,
    with_resizer: bool = False,
    with_toolbar: bool = False,
    style: str = "tailwind",
) -> dict:
    """Generate a custom React Flow node component.

    Returns a dict {"component": tsx, "registration": ts, "usage": ts, "type_name": str,
                    "warnings": [str]}.
    """
    warnings: list[str] = []

    if not name:
        raise ValueError("name is required")
    component_name = name if PASCAL_RE.match(name) else _to_pascal(name)
    if component_name != name:
        warnings.append(f"name '{name}' normalized to PascalCase '{component_name}'.")
    type_name = component_name[0].lower() + component_name[1:]  # camelCase for the nodeTypes key

    if style not in VALID_STYLES:
        raise ValueError(f"style must be one of {sorted(VALID_STYLES)}")

    # data fields
    data_fields = data_fields or []
    normalized_fields: list[dict] = []
    for f in data_fields:
        if "name" not in f:
            raise ValueError(f"data_fields entry missing 'name': {f}")
        normalized_fields.append({
            "name": f["name"],
            "type": f.get("type") or _ts_type_for_default(f.get("default")) or "unknown",
            "default": f.get("default"),
        })

    # handles
    if handles is None:
        handles = [
            {"kind": "target", "position": "left", "id": None},
            {"kind": "source", "position": "right", "id": None},
        ]
    normalized_handles: list[dict] = []
    for h in handles:
        kind = h.get("kind") or h.get("type")
        if kind not in VALID_HANDLE_KINDS:
            raise ValueError(f"handle kind must be source|target, got {kind!r}")
        pos = h.get("position", "").lower()
        if pos not in VALID_POSITIONS:
            raise ValueError(f"handle position must be one of {sorted(VALID_POSITIONS)}, got {pos!r}")
        normalized_handles.append({"kind": kind, "position": pos, "id": h.get("id") or None})

    # editable requires at least one string-typed field
    if editable and not any(f["type"] == "string" for f in normalized_fields):
        warnings.append("editable=true but no string-typed data_field; UI will render no inputs.")

    # build the TSX
    data_type = component_name + "Data"
    type_alias_lines = [f"export type {data_type} = {{"]
    for f in normalized_fields:
        type_alias_lines.append(f"  {f['name']}: {f['type']};")
    if not normalized_fields:
        type_alias_lines.append("  // (no data fields)")
    type_alias_lines.append("};")
    type_alias = "\n".join(type_alias_lines)

    imports = [
        'import { type NodeProps, Handle, Position'
        + (", useReactFlow" if editable else "")
        + (", NodeResizer" if with_resizer else "")
        + (", NodeToolbar" if with_toolbar else "")
        + ' } from "@xyflow/react";',
    ]

    handle_lines = []
    for i, h in enumerate(normalized_handles):
        pos_enum = "Position." + h["position"].capitalize()
        kind = h["kind"]
        id_attr = f' id="{h["id"]}"' if h["id"] else ""
        handle_lines.append(f'      <Handle type="{kind}" position={{{pos_enum}}}{id_attr} />')

    toolbar_block = ""
    if with_toolbar:
        toolbar_block = """      <NodeToolbar isVisible={selected} position={Position.Top}>
        <button onClick={() => deleteNode()}>Delete</button>
      </NodeToolbar>
"""

    resizer_block = ""
    if with_resizer:
        resizer_block = "      <NodeResizer isVisible={selected} minWidth={120} minHeight={60} />\n"

    # inner body — wrapper styling per style choice
    if style == "tailwind":
        wrapper_open = '<div className={`rounded-md border bg-white px-3 py-2 shadow-sm ${selected ? "ring-2 ring-blue-500" : "border-slate-300"}`}>'
    elif style == "css-modules":
        wrapper_open = (
            'import styles from "./' + component_name + '.module.css";\n'
            '\n'
            '// Wrapper uses styles.node + styles.selected\n'
            '// ...'
        )
        # In actual JSX:
        wrapper_open = '<div className={selected ? `${styles.node} ${styles.selected}` : styles.node}>'
    else:  # inline
        wrapper_open = (
            '<div style={{ border: `1px solid ${selected ? "#3b82f6" : "#cbd5e1"}`, '
            'borderRadius: 6, padding: "8px 12px", background: "white", '
            'boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>'
        )

    # body fields rendering — style-aware
    body_field_lines: list[str] = []
    use_tailwind = style == "tailwind"
    for f in normalized_fields:
        if editable and f["type"] == "string":
            if use_tailwind:
                body_field_lines.append(
                    '      <label className="flex flex-col text-xs">\n'
                    f'        <span className="text-slate-500">{f["name"]}</span>\n'
                    f'        <input className="nodrag mt-1 rounded border border-slate-200 px-2 py-1"\n'
                    f'          value={{data.{f["name"]} ?? ""}}\n'
                    f'          onChange={{(e) => updateNodeData(id, {{ {f["name"]}: e.target.value }})}}\n'
                    "        />\n"
                    "      </label>"
                )
            else:
                body_field_lines.append(
                    '      <label style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>\n'
                    f'        <span style={{{{ color: "#64748b" }}}}>{f["name"]}</span>\n'
                    f'        <input className="nodrag" style={{{{ marginTop: 4, borderRadius: 4, border: "1px solid #e2e8f0", padding: "4px 8px" }}}}\n'
                    f'          value={{data.{f["name"]} ?? ""}}\n'
                    f'          onChange={{(e) => updateNodeData(id, {{ {f["name"]}: e.target.value }})}}\n'
                    "        />\n"
                    "      </label>"
                )
        else:
            if use_tailwind:
                body_field_lines.append(
                    f'      <div className="text-xs"><span className="text-slate-500">{f["name"]}:</span> '
                    f"{{String(data.{f['name']} ?? '')}}</div>"
                )
            else:
                body_field_lines.append(
                    f'      <div style={{{{ fontSize: 12 }}}}><span style={{{{ color: "#64748b" }}}}>{f["name"]}:</span> '
                    f"{{String(data.{f['name']} ?? '')}}</div>"
                )
    if not body_field_lines:
        if use_tailwind:
            body_field_lines.append('      <div className="text-sm font-medium">{`' + component_name + "`}</div>")
        else:
            body_field_lines.append(
                '      <div style={{ fontSize: 14, fontWeight: 500 }}>{`' + component_name + "`}</div>"
            )

    use_react_flow_hook = ""
    delete_callback = ""
    if editable:
        use_react_flow_hook = "  const { updateNodeData } = useReactFlow();\n"
    if with_toolbar:
        delete_callback = (
            "  const { deleteElements } = useReactFlow();\n"
            "  const deleteNode = () => deleteElements({ nodes: [{ id }] });\n"
        )
    # If editable AND with_toolbar both call useReactFlow, dedupe:
    if editable and with_toolbar:
        use_react_flow_hook = "  const { updateNodeData, deleteElements } = useReactFlow();\n"
        delete_callback = "  const deleteNode = () => deleteElements({ nodes: [{ id }] });\n"

    component = f"""{chr(10).join(imports)}

{type_alias}

export function {component_name}({{ id, data, selected }}: NodeProps<{{ id: string; data: {data_type}; type: '{type_name}' }}>) {{
{use_react_flow_hook}{delete_callback}  return (
    <>
{toolbar_block}{resizer_block}      {wrapper_open}
{chr(10).join(body_field_lines)}
      </div>
{chr(10).join(handle_lines)}
    </>
  );
}}
"""

    # registration snippet
    registration = f"""// Declare OUTSIDE the parent component (or wrap in useMemo) — re-creating nodeTypes per render
// triggers the React Flow "(re)created" warning + perf regression.
const nodeTypes = {{
  {type_name}: {component_name},
}};

<ReactFlow nodes={{nodes}} edges={{edges}} nodeTypes={{nodeTypes}} … />
"""

    # usage / factory snippet
    default_data_pairs = []
    for f in normalized_fields:
        if f["default"] is not None:
            literal = repr(f["default"]) if isinstance(f["default"], str) else str(f["default"]).lower() if isinstance(f["default"], bool) else str(f["default"])
            default_data_pairs.append(f"{f['name']}: {literal}")
        elif f["type"] == "string":
            default_data_pairs.append(f"{f['name']}: ''")
        elif f["type"] == "number":
            default_data_pairs.append(f"{f['name']}: 0")
        elif f["type"] == "boolean":
            default_data_pairs.append(f"{f['name']}: false")
    data_literal = "{ " + ", ".join(default_data_pairs) + " }" if default_data_pairs else "{}"

    usage = f"""const initialNodes: Node[] = [
  {{
    id: 'n1',
    type: '{type_name}',
    position: {{ x: 100, y: 100 }},
    data: {data_literal},
  }},
];
"""

    return {
        "component_name": component_name,
        "type_name": type_name,
        "component": component,
        "registration": registration,
        "usage": usage,
        "warnings": warnings,
    }


# ───────────────────────── edge scaffolder ─────────────────────────


def scaffold_custom_edge(
    *,
    name: str,
    path_type: str = "bezier",
    with_label: bool = False,
    with_delete_button: bool = False,
    with_label_renderer: bool = False,
    style: str = "tailwind",
) -> dict:
    """Generate a custom React Flow edge component.

    Returns dict {"component": tsx, "registration": ts, "usage": ts, "type_name": str,
                  "warnings": [str]}.
    """
    warnings: list[str] = []

    if not name:
        raise ValueError("name is required")
    component_name = name if PASCAL_RE.match(name) else _to_pascal(name)
    if component_name != name:
        warnings.append(f"name '{name}' normalized to PascalCase '{component_name}'.")
    type_name = component_name[0].lower() + component_name[1:]

    if path_type not in VALID_PATH_TYPES:
        raise ValueError(f"path_type must be one of {sorted(VALID_PATH_TYPES)}")
    if style not in VALID_STYLES:
        raise ValueError(f"style must be one of {sorted(VALID_STYLES)}")
    if with_delete_button and not with_label_renderer:
        warnings.append("with_delete_button=true forces with_label_renderer=true (button needs HTML overlay).")
        with_label_renderer = True

    path_fn = {
        "bezier": "getBezierPath",
        "smoothstep": "getSmoothStepPath",
        "step": "getSmoothStepPath",  # step = smoothstep with borderRadius 0
        "straight": "getStraightPath",
        "simplebezier": "getSimpleBezierPath",
    }[path_type]
    path_args_extra = ", borderRadius: 0" if path_type == "step" else ""

    label_imports = []
    if with_label_renderer:
        label_imports.append("EdgeLabelRenderer")
    if with_delete_button:
        label_imports.append("useReactFlow")

    extra_imports = (", " + ", ".join(label_imports)) if label_imports else ""

    imports = (
        f'import {{ BaseEdge, {path_fn}, type EdgeProps{extra_imports} }} from "@xyflow/react";'
    )

    # body
    delete_hook = ""
    delete_button_block = ""
    if with_delete_button:
        delete_hook = "  const { setEdges } = useReactFlow();\n"
        if style == "tailwind":
            btn_class = 'className="nodrag nopan pointer-events-auto rounded bg-white border border-slate-300 px-1.5 py-0.5 text-xs shadow"'
        else:
            btn_class = 'style={{ pointerEvents: "all", background: "white", border: "1px solid #cbd5e1", borderRadius: 4, padding: "2px 6px", fontSize: 11 }} className="nodrag nopan"'
        delete_button_block = f"""        <button {btn_class}
          onClick={{() => setEdges((es) => es.filter((e) => e.id !== id))}}
        >×</button>"""

    label_block = ""
    if with_label_renderer:
        label_inner_parts = []
        if with_label:
            if style == "tailwind":
                label_inner_parts.append('        <span className="text-xs text-slate-700">{label}</span>')
            else:
                label_inner_parts.append('        <span style={{ fontSize: 11, color: "#334155" }}>{label}</span>')
        if delete_button_block:
            label_inner_parts.append(delete_button_block)
        if style == "tailwind":
            wrapper_open = '<div className="nodrag nopan pointer-events-none absolute flex items-center gap-1" style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}>'
        else:
            wrapper_open = (
                '<div className="nodrag nopan" style={{ position: "absolute", pointerEvents: "none", '
                'display: "flex", alignItems: "center", gap: 4, '
                'transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}>'
            )
        label_block = f"""      <EdgeLabelRenderer>
        {wrapper_open}
{chr(10).join(label_inner_parts) if label_inner_parts else ''}
        </div>
      </EdgeLabelRenderer>
"""

    label_destructure = ", label" if with_label and not with_label_renderer else (", label" if with_label_renderer and with_label else "")

    component = f"""{imports}

export function {component_name}({{
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  markerStart,
  style{label_destructure},
}}: EdgeProps) {{
{delete_hook}  const [edgePath, labelX, labelY] = {path_fn}({{
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition{path_args_extra},
  }});

  return (
    <>
      <BaseEdge id={{id}} path={{edgePath}} markerEnd={{markerEnd}} markerStart={{markerStart}} style={{style}} />
{label_block}    </>
  );
}}
"""

    registration = f"""// Declare OUTSIDE the parent component (or useMemo)
const edgeTypes = {{
  {type_name}: {component_name},
}};

<ReactFlow nodes={{nodes}} edges={{edges}} edgeTypes={{edgeTypes}} … />
"""

    label_field = ', label: "connects"' if with_label else ""
    usage = f"""const initialEdges: Edge[] = [
  {{
    id: 'e1-2',
    source: 'n1',
    target: 'n2',
    type: '{type_name}'{label_field},
  }},
];
"""

    return {
        "component_name": component_name,
        "type_name": type_name,
        "component": component,
        "registration": registration,
        "usage": usage,
        "warnings": warnings,
    }
