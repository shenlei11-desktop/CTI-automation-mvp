# Starts the backend (uvicorn) and frontend (vite) together for local dev.
# One-time setup first (see README "Option B"): create .venv + pip install +
# spacy download, and `npm install` in frontend/.

$backend = Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app", "--reload" `
    -NoNewWindow -PassThru

try {
    Push-Location frontend
    npm run dev
}
finally {
    Pop-Location
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}
