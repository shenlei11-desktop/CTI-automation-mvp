import { useEffect, useState } from "react"
import { getAdvisoryFeed } from "../api/client"
import type { FeedItem } from "../api/types"

interface Props {
  onSelect: (item: FeedItem) => void
  disabled: boolean
}

type FeedState = "loading" | "ok" | "unavailable"

export default function LiveAdvisoryPicker({ onSelect, disabled }: Props) {
  const [items, setItems] = useState<FeedItem[]>([])
  const [state, setState] = useState<FeedState>("loading")

  useEffect(() => {
    let cancelled = false
    getAdvisoryFeed(6)
      .then((res) => {
        if (cancelled) return
        setItems(res.items)
        setState(res.items.length > 0 ? "ok" : "unavailable")
      })
      .catch(() => {
        if (!cancelled) setState("unavailable")
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (state === "loading") {
    return <p className="font-mono text-xs text-stone-500">fetching live CISA ICS advisories…</p>
  }

  if (state === "unavailable") {
    return (
      <p className="font-mono text-xs text-stone-500">
        live feed unavailable right now — the canned examples below still work.
      </p>
    )
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {items.map((item) => (
        <button
          key={item.url}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(item)}
          className="border border-stone-800 bg-stone-900/40 px-3 py-2 text-left text-sm text-stone-300 transition-colors hover:border-amber-500/50 hover:text-amber-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <div className="truncate">{item.title}</div>
          {item.published && (
            <div className="mt-0.5 font-mono text-[11px] text-stone-600">{item.published}</div>
          )}
        </button>
      ))}
    </div>
  )
}
