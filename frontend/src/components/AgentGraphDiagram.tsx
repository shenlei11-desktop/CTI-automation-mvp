interface Props {
  /** Node ids from a real AdvisoryResponse.trace, in order, e.g.
   * ["extraction","classification","triage","finalize"]. When given, the taken path
   * is highlighted and untaken nodes/edges dim -- used on the Demo page to show the
   * actual run. Omitted on the Overview page for the static topology view. */
  activeTrace?: string[]
  /** The Overview page embeds this on a light "document" panel; the Demo page on a
   * dark "console" panel -- stroke/fill colors flip accordingly. */
  theme?: "light" | "dark"
}

const PALETTE = {
  light: {
    stroke: "#57534e", // stone-600
    strokeDim: "#d6d3d1", // stone-300
    fill: "#fafaf9", // stone-50
    fillDim: "#fafaf9",
    text: "#292524", // stone-800
    textDim: "#a8a29e", // stone-400
    active: "#991b1b", // red-800
    activeFill: "#fef2f2", // red-50
    branchRed: "#991b1b",
    branchAmber: "#b45309", // amber-700
  },
  dark: {
    stroke: "#78716c", // stone-500
    strokeDim: "#44403c", // stone-700
    fill: "#0c0a09", // stone-950
    fillDim: "#0c0a09",
    text: "#e7e5e4", // stone-200
    textDim: "#57534e", // stone-600
    active: "#f59e0b", // amber-500
    activeFill: "#1c1917",
    branchRed: "#f87171", // red-400
    branchAmber: "#fbbf24", // amber-400
  },
} as const

interface NodeDef {
  id: string
  label: string
  sub?: string
  x: number
  y: number
  w: number
  h: number
  kind: "process" | "terminal" | "pre"
}

const W = 640
const NODES: NodeDef[] = [
  { id: "ingestion", label: "Ingestion", sub: "PDF / HTML / URL → text", x: 220, y: 16, w: 200, h: 52, kind: "pre" },
  { id: "extraction", label: "Extraction", sub: "IOCs + entities", x: 220, y: 128, w: 200, h: 52, kind: "process" },
  {
    id: "classification",
    label: "Classification",
    sub: "ATT&CK-for-ICS matching",
    x: 220,
    y: 296,
    w: 200,
    h: 52,
    kind: "process",
  },
  { id: "triage", label: "Triage", sub: "severity cascade", x: 220, y: 384, w: 200, h: 52, kind: "process" },
  { id: "finalize", label: "Advisory", sub: "rendered + full trace", x: 220, y: 552, w: 200, h: 52, kind: "terminal" },
  {
    id: "needs_extraction_review",
    label: "Needs Extraction Review",
    sub: "hard stop",
    x: 460,
    y: 208,
    w: 160,
    h: 52,
    kind: "terminal",
  },
  {
    id: "needs_clarification",
    label: "Needs Clarification",
    sub: "provisional score kept",
    x: 460,
    y: 464,
    w: 160,
    h: 52,
    kind: "terminal",
  },
]

const nodeById = Object.fromEntries(NODES.map((n) => [n.id, n]))

function centerBottom(id: string) {
  const n = nodeById[id]
  return { x: n.x + n.w / 2, y: n.y + n.h }
}
function centerTop(id: string) {
  const n = nodeById[id]
  return { x: n.x + n.w / 2, y: n.y }
}
function centerLeft(id: string) {
  const n = nodeById[id]
  return { x: n.x, y: n.y + n.h / 2 }
}
function rightMid(id: string) {
  const n = nodeById[id]
  return { x: n.x + n.w, y: n.y + n.h / 2 }
}

export default function AgentGraphDiagram({ activeTrace, theme = "light" }: Props) {
  const p = PALETTE[theme]
  const active = new Set(activeTrace ?? [])
  const isLive = Boolean(activeTrace && activeTrace.length > 0)

  function nodeStroke(id: string) {
    if (!isLive) return p.stroke
    return active.has(id) ? p.active : p.strokeDim
  }
  function nodeFill(id: string) {
    if (!isLive) return p.fill
    return active.has(id) ? p.activeFill : p.fillDim
  }
  function nodeTextColor(id: string) {
    if (!isLive) return p.text
    return active.has(id) ? p.text : p.textDim
  }
  function edgeActive(fromId: string, toId: string) {
    if (!isLive || !activeTrace) return false
    const i = activeTrace.indexOf(fromId)
    return i !== -1 && activeTrace[i + 1] === toId
  }
  function edgeStroke(fromId: string, toId: string) {
    return edgeActive(fromId, toId) ? p.active : isLive ? p.strokeDim : p.stroke
  }

  const height = 632

  return (
    <svg
      viewBox={`0 0 ${W} ${height}`}
      className="w-full"
      role="img"
      aria-label="Agent graph: ingestion, extraction, classification, triage, and advisory, with conditional edges for extraction review and clarification"
    >
      <defs>
        <marker id={`arrow-${theme}`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill={p.stroke} />
        </marker>
        <marker id={`arrow-active-${theme}`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill={p.active} />
        </marker>
      </defs>

      {/* ingestion -> extraction: dashed, a separate API call, not part of the graph */}
      <line
        x1={centerBottom("ingestion").x}
        y1={centerBottom("ingestion").y}
        x2={centerTop("extraction").x}
        y2={centerTop("extraction").y}
        stroke={edgeStroke("ingestion", "extraction")}
        strokeWidth="1.5"
        strokeDasharray="4 3"
        markerEnd={`url(#${edgeActive("ingestion", "extraction") ? `arrow-active-${theme}` : `arrow-${theme}`})`}
      />

      {/* extraction -> classification (proceed path, straight down) */}
      <line
        x1={centerBottom("extraction").x}
        y1={centerBottom("extraction").y}
        x2={centerTop("classification").x}
        y2={172}
        stroke={edgeStroke("extraction", "classification")}
        strokeWidth="1.5"
        markerEnd={`url(#${edgeActive("extraction", "classification") ? `arrow-active-${theme}` : `arrow-${theme}`})`}
      />
      <text x={centerBottom("extraction").x + 8} y={190} fontSize="10" fill={p.textDim} className="font-mono">
        proceed
      </text>

      {/* extraction -> needs_extraction_review (flag_for_review, branches right) */}
      <path
        d={`M ${rightMid("extraction").x},${rightMid("extraction").y} L ${rightMid("extraction").x + 40},${rightMid("extraction").y} L ${rightMid("extraction").x + 40},${centerLeft("needs_extraction_review").y} L ${centerLeft("needs_extraction_review").x},${centerLeft("needs_extraction_review").y}`}
        fill="none"
        stroke={edgeActive("extraction", "needs_extraction_review") ? p.branchRed : edgeStroke("extraction", "needs_extraction_review")}
        strokeWidth="1.5"
        markerEnd={`url(#${edgeActive("extraction", "needs_extraction_review") ? `arrow-active-${theme}` : `arrow-${theme}`})`}
      />
      <text
        x={rightMid("extraction").x + 46}
        y={rightMid("extraction").y - 6}
        fontSize="10"
        fill={isLive && !active.has("needs_extraction_review") ? p.textDim : p.branchRed}
        className="font-mono"
      >
        flag_for_review
      </text>

      {/* classification -> triage (unconditional) */}
      <line
        x1={centerBottom("classification").x}
        y1={centerBottom("classification").y}
        x2={centerTop("triage").x}
        y2={centerTop("triage").y}
        stroke={edgeStroke("classification", "triage")}
        strokeWidth="1.5"
        markerEnd={`url(#${edgeActive("classification", "triage") ? `arrow-active-${theme}` : `arrow-${theme}`})`}
      />

      {/* triage -> finalize (scored path, straight down) */}
      <line
        x1={centerBottom("triage").x}
        y1={centerBottom("triage").y}
        x2={centerTop("finalize").x}
        y2={centerTop("finalize").y}
        stroke={edgeStroke("triage", "finalize")}
        strokeWidth="1.5"
        markerEnd={`url(#${edgeActive("triage", "finalize") ? `arrow-active-${theme}` : `arrow-${theme}`})`}
      />
      <text x={centerBottom("triage").x + 8} y={452} fontSize="10" fill={p.textDim} className="font-mono">
        scored
      </text>

      {/* triage -> needs_clarification (branches right) */}
      <path
        d={`M ${rightMid("triage").x},${rightMid("triage").y} L ${rightMid("triage").x + 40},${rightMid("triage").y} L ${rightMid("triage").x + 40},${centerLeft("needs_clarification").y} L ${centerLeft("needs_clarification").x},${centerLeft("needs_clarification").y}`}
        fill="none"
        stroke={edgeActive("triage", "needs_clarification") ? p.branchAmber : edgeStroke("triage", "needs_clarification")}
        strokeWidth="1.5"
        markerEnd={`url(#${edgeActive("triage", "needs_clarification") ? `arrow-active-${theme}` : `arrow-${theme}`})`}
      />
      <text
        x={rightMid("triage").x + 46}
        y={rightMid("triage").y - 6}
        fontSize="10"
        fill={isLive && !active.has("needs_clarification") ? p.textDim : p.branchAmber}
        className="font-mono"
      >
        needs_clarification
      </text>

      {/* decision diamonds */}
      {[
        { after: "extraction", cy: 154 },
        { after: "triage", cy: 410 },
      ].map(({ after, cy }) => (
        <rect
          key={after}
          x={centerBottom(after).x - 6}
          y={cy - 6}
          width={12}
          height={12}
          transform={`rotate(45 ${centerBottom(after).x} ${cy})`}
          fill={p.fill}
          stroke={p.stroke}
          strokeWidth="1.5"
        />
      ))}

      {/* nodes */}
      {NODES.map((n) => (
        <g key={n.id}>
          <rect
            x={n.x}
            y={n.y}
            width={n.w}
            height={n.h}
            rx={n.kind === "terminal" ? 2 : 0}
            fill={nodeFill(n.id)}
            stroke={nodeStroke(n.id)}
            strokeWidth={n.kind === "pre" ? 1.25 : 1.5}
            strokeDasharray={n.kind === "pre" ? "4 3" : undefined}
          />
          <text
            x={n.x + n.w / 2}
            y={n.y + n.h / 2 - (n.sub ? 6 : 0)}
            textAnchor="middle"
            fontSize="13"
            fontWeight={600}
            fill={nodeTextColor(n.id)}
            className="font-serif"
          >
            {n.label}
          </text>
          {n.sub && (
            <text
              x={n.x + n.w / 2}
              y={n.y + n.h / 2 + 12}
              textAnchor="middle"
              fontSize="9.5"
              fill={active.has(n.id) || !isLive ? p.textDim : p.textDim}
              className="font-mono"
            >
              {n.sub}
            </text>
          )}
        </g>
      ))}
    </svg>
  )
}
