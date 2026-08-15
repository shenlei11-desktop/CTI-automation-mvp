interface Props {
  theme?: "light" | "dark"
}

const PALETTE = {
  light: {
    stroke: "#57534e",
    text: "#292524",
    textDim: "#78716c",
    fillWide: "#f5f5f4",
    fillNarrow: "#e7e5e4",
    proceed: "#166534",
    review: "#b45309",
  },
  dark: {
    stroke: "#78716c",
    text: "#e7e5e4",
    textDim: "#a8a29e",
    fillWide: "#1c1917",
    fillNarrow: "#292524",
    proceed: "#4ade80",
    review: "#fbbf24",
  },
} as const

/** A trapezoid representing a narrowing (or widening) stage of the funnel. */
function Stage({
  y,
  h,
  topW,
  bottomW,
  cx,
  fill,
  stroke,
}: {
  y: number
  h: number
  topW: number
  bottomW: number
  cx: number
  fill: string
  stroke: string
}) {
  const points = [
    [cx - topW / 2, y],
    [cx + topW / 2, y],
    [cx + bottomW / 2, y + h],
    [cx - bottomW / 2, y + h],
  ]
    .map((p) => p.join(","))
    .join(" ")
  return <polygon points={points} fill={fill} stroke={stroke} strokeWidth="1.25" />
}

export default function ClassificationFunnelDiagram({ theme = "light" }: Props) {
  const p = PALETTE[theme]
  const cx = 320
  const W = 640

  return (
    <svg
      viewBox={`0 0 ${W} 430`}
      className="w-full"
      role="img"
      aria-label="Classification funnel: 79 techniques narrowed by embedding retrieval, reordered by cross-encoder reranking, then gated on score margin into proceed or flag for review"
    >
      <Stage y={16} h={70} topW={520} bottomW={520} cx={cx} fill={p.fillWide} stroke={p.stroke} />
      <text x={cx} y={44} textAnchor="middle" fontSize="14" fontWeight={600} fill={p.text} className="font-serif">
        79 ATT&amp;CK-for-ICS techniques
      </text>
      <text x={cx} y={62} textAnchor="middle" fontSize="10" fill={p.textDim} className="font-mono">
        the full corpus, every request starts here
      </text>

      <line x1={cx} y1={86} x2={cx} y2={112} stroke={p.stroke} strokeWidth="1.25" />
      <text x={cx + 12} y={104} fontSize="10.5" fill={p.textDim} className="font-mono">
        embed (bge-base-en-v1.5) → cosine similarity
      </text>

      <Stage y={112} h={64} topW={520} bottomW={300} cx={cx} fill={p.fillWide} stroke={p.stroke} />
      <text x={cx} y={148} textAnchor="middle" fontSize="13" fontWeight={600} fill={p.text} className="font-serif">
        top 50 candidates
      </text>
      <text x={cx} y={164} textAnchor="middle" fontSize="9.5" fill={p.textDim} className="font-mono">
        recall@50 = 0.967 on 259 labeled examples
      </text>

      <line x1={cx} y1={176} x2={cx} y2={202} stroke={p.stroke} strokeWidth="1.25" />
      <text x={cx + 12} y={194} fontSize="10.5" fill={p.textDim} className="font-mono">
        rerank (cross-encoder, ms-marco-MiniLM) → reorder
      </text>

      <Stage y={202} h={56} topW={300} bottomW={220} cx={cx} fill={p.fillNarrow} stroke={p.stroke} />
      <text x={cx} y={234} textAnchor="middle" fontSize="12.5" fontWeight={600} fill={p.text} className="font-serif">
        ranked candidates
      </text>
      <text x={cx} y={249} textAnchor="middle" fontSize="9.5" fill={p.textDim} className="font-mono">
        raw logits, not probabilities
      </text>

      <line x1={cx} y1={258} x2={cx} y2={284} stroke={p.stroke} strokeWidth="1.25" />
      <text x={cx + 12} y={276} fontSize="10.5" fill={p.textDim} className="font-mono">
        margin gate: top1 − top2 vs 1.25
      </text>

      {/* fork into proceed / flag_for_review */}
      <path
        d={`M ${cx},284 L ${cx},300 L ${cx - 130},300 L ${cx - 130},324`}
        fill="none"
        stroke={p.stroke}
        strokeWidth="1.25"
      />
      <path
        d={`M ${cx},284 L ${cx},300 L ${cx + 130},300 L ${cx + 130},324`}
        fill="none"
        stroke={p.stroke}
        strokeWidth="1.25"
      />

      <rect x={cx - 140 - 100} y={324} width={200} height={64} fill="none" stroke={p.proceed} strokeWidth="1.5" />
      <text
        x={cx - 140}
        y={350}
        textAnchor="middle"
        fontSize="13"
        fontWeight={600}
        fill={p.proceed}
        className="font-serif"
      >
        proceed
      </text>
      <text x={cx - 140} y={368} textAnchor="middle" fontSize="9.5" fill={p.textDim} className="font-mono">
        margin ≥ 1.25
      </text>

      <rect x={cx + 140 - 100} y={324} width={200} height={64} fill="none" stroke={p.review} strokeWidth="1.5" />
      <text
        x={cx + 140}
        y={346}
        textAnchor="middle"
        fontSize="13"
        fontWeight={600}
        fill={p.review}
        className="font-serif"
      >
        flag_for_review
      </text>
      <text x={cx + 140} y={364} textAnchor="middle" fontSize="9.5" fill={p.textDim} className="font-mono">
        margin &lt; 1.25
      </text>
      <text x={cx + 140} y={378} textAnchor="middle" fontSize="9.5" fill={p.textDim} className="font-mono">
        too close to call
      </text>

      <text x={cx} y={410} textAnchor="middle" fontSize="10" fill={p.textDim} className="font-mono">
        threshold derived via Youden's J over 259 labeled examples, not guessed
      </text>
    </svg>
  )
}
