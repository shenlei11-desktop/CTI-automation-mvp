import { NavLink } from "react-router-dom"

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? "bg-teal-500/15 text-teal-300" : "text-slate-400 hover:text-slate-200"
  }`

export default function NavBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <NavLink to="/" className="flex items-center gap-2 text-slate-200">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-500/20 text-sm font-bold text-teal-300">
            CT
          </span>
          <span className="font-semibold tracking-tight">CTI/ICS Triage</span>
        </NavLink>
        <nav className="flex gap-1">
          <NavLink to="/" end className={linkClasses}>
            Overview
          </NavLink>
          <NavLink to="/demo" className={linkClasses}>
            Try It
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
