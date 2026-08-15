interface Props {
  theme?: "light" | "dark"
}

const PALETTE = {
  light: {
    stroke: "#57534e",
    text: "#292524",
    textDim: "#78716c",
    rungFill: "#f5f5f4",
    critical: "#991b1b",
    high: "#c2410c",
    medium: "#b45309",
    low: "#166534",
  },
  dark: {
    stroke: "#78716c",
    text: "#e7e5e4",
    textDim: "#a8a29e",
    rungFill: "#1c1917",
    critical: "#f87171",
    high: "#fb923c",
    medium: "#fbbf24",
    low: "#4ade80",
  },
} as const

const BANDS = [
  { label: "Low", key: "low" as const },
  { label: "Medium", key: "medium" as const },
  { label: "High", key: "high" as const },
  { label: "Critical", key: "critical" as const },
]

export default function SeverityCascadeDiagram({ theme = "light" }: Props) {
  const p = PALETTE[theme]
  const W = 640
  const rungH = 48
  const rungGap = 34
  const startY = 24
  const rungX = 150
  const rungW = 190
  const step = rungH + rungGap

  const yFor = (i: number) => startY + (BANDS.length - 1 - i) * step

  return (
    <svg
      viewBox={`0 0 ${W} 400`}
      className="w-full"
      role="img"
      aria-label="Severity cascade: CVSS base band, escalated by exposure and asset criticality, with CISA KEV listing as a floor at High"
    >
      <defs>
        <marker id={`sev-arrow-${theme}`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill={p.stroke} />
        </marker>
      </defs>

      {/* the ladder */}
      {BANDS.map((band, i) => (
        <g key={band.key}>
          <rect
            x={rungX}
            y={yFor(i)}
            width={rungW}
            height={rungH}
            fill={p.rungFill}
            stroke={p[band.key]}
            strokeWidth="1.5"
          />
          <text
            x={rungX + rungW / 2}
            y={yFor(i) + rungH / 2 + 5}
            textAnchor="middle"
            fontSize="14"
            fontWeight={600}
            fill={p[band.key]}
            className="font-serif"
          >
            {band.label}
          </text>
        </g>
      ))}

      {/* CVSS base entry, pointing at Medium (the documented neutral default) */}
      <text x={rungX - 14} y={yFor(1) + rungH / 2 + 4} textAnchor="end" fontSize="10.5" fill={p.textDim} className="font-mono">
        CVSS base band →
      </text>

      {/* escalation arrows, each with its own dedicated vertical space */}
      <line
        x1={rungX + rungW + 20}
        y1={yFor(1) + 6}
        x2={rungX + rungW + 20}
        y2={yFor(2) + rungH - 6}
        stroke={p.stroke}
        strokeWidth="1.25"
        markerEnd={`url(#sev-arrow-${theme})`}
      />
      <text x={rungX + rungW + 30} y={(yFor(1) + yFor(2) + rungH) / 2 + 4} fontSize="11" fill={p.textDim} className="font-mono">
        internet-facing exposure: +1 band
      </text>

      <line
        x1={rungX + rungW + 20}
        y1={yFor(2) + 6}
        x2={rungX + rungW + 20}
        y2={yFor(3) + rungH - 6}
        stroke={p.stroke}
        strokeWidth="1.25"
        markerEnd={`url(#sev-arrow-${theme})`}
      />
      <text x={rungX + rungW + 30} y={(yFor(2) + yFor(3) + rungH) / 2 + 4} fontSize="11" fill={p.textDim} className="font-mono">
        safety-critical asset: +1 band
      </text>

      {/* KEV floor, drawn as an actual floor line at the High/Critical boundary,
          captioned well below the ladder to avoid colliding with the escalation labels */}
      <line
        x1={rungX - 24}
        y1={yFor(2)}
        x2={rungX + rungW + 130}
        y2={yFor(2)}
        stroke={p.critical}
        strokeWidth="2"
        strokeDasharray="6 3"
      />

      <text x={rungX} y={yFor(0) + rungH + 40} fontSize="11" fontWeight={600} fill={p.critical} className="font-mono">
        ─ ─ CISA KEV listed: floor at High, regardless of the steps above
      </text>
      <text x={rungX} y={yFor(0) + rungH + 62} fontSize="10.5" fill={p.textDim} className="font-mono">
        every step — including no-ops — is recorded in the rule_trace
      </text>
    </svg>
  )
}
