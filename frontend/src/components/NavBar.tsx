import { NavLink } from "react-router-dom"

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  `rounded px-3 py-1.5 text-sm font-medium tracking-wide transition-colors ${
    isActive ? "bg-amber-500/15 text-amber-300" : "text-stone-400 hover:text-stone-200"
  }`

export default function NavBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-stone-800 bg-stone-950/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <NavLink to="/" className="flex items-center gap-2.5 text-stone-100">
          <span className="flex h-7 w-7 items-center justify-center border border-amber-500/40 text-sm font-bold text-amber-400">
            §
          </span>
          <span className="font-serif text-base tracking-wide">CTI / ICS Triage</span>
        </NavLink>
        <nav className="flex gap-1 text-xs uppercase">
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
