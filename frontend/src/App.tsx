import { BrowserRouter, Route, Routes } from "react-router-dom"
import NavBar from "./components/NavBar"
import HomePage from "./pages/HomePage"
import DemoPage from "./pages/DemoPage"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-full flex-col">
        <NavBar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/demo" element={<DemoPage />} />
          </Routes>
        </main>
        <footer className="border-t border-stone-800 bg-stone-950 px-6 py-6 text-center text-xs text-stone-600">
          Built for a DigiSpec application portfolio. All sample data is synthetic
          unless fetched live from a real source you provide.
        </footer>
      </div>
    </BrowserRouter>
  )
}
