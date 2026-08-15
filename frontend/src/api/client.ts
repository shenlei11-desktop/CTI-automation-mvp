import type { AdvisoryResponse, FeedResponse, IngestResponse } from "./types"

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
          ? body.detail.map((e: { msg?: string }) => e.msg).join("; ")
          : res.statusText
    throw new ApiError(detail, res.status)
  }
  return res.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return handle<T>(res)
}

export function ingestText(text: string): Promise<IngestResponse> {
  return postJson("/ingest", { source_type: "text", text })
}

export function ingestHtml(html: string): Promise<IngestResponse> {
  return postJson("/ingest", { source_type: "html", text: html })
}

export function ingestUrl(url: string): Promise<IngestResponse> {
  return postJson("/ingest", { source_type: "url", url })
}

export async function ingestPdf(file: File): Promise<IngestResponse> {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${API_BASE}/ingest/pdf`, { method: "POST", body: form })
  return handle<IngestResponse>(res)
}

export function getAdvisory(text: string, reportId?: string): Promise<AdvisoryResponse> {
  return postJson("/advisory", { text, report_id: reportId ?? null })
}

export async function getAdvisoryFeed(limit = 6): Promise<FeedResponse> {
  const res = await fetch(`${API_BASE}/ingest/feed?limit=${limit}`)
  return handle<FeedResponse>(res)
}
