import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/', glyph: '神', label: 'Home' },
  { to: '/session', glyph: '◎', label: 'Session' },
  { to: '/brief', glyph: '▤', label: 'Brief' },
  { to: '/debrief', glyph: '◈', label: 'Debrief' },
]

/** The layout law: nav strip, sensei rail, workspace. */
export default function Dojo({ rail, children }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-ink">
      <nav className="flex w-[46px] shrink-0 flex-col items-center gap-4 bg-ink py-4">
        {NAV.map(({ to, glyph, label }) => (
          <NavLink key={to} to={to} end={to === '/'} title={label}
            className={({ isActive }) =>
              `font-serif text-[15px] transition-colors ${
                isActive ? 'text-gold' : 'text-washi/30 hover:text-washi/60'}`}>
            {glyph}
          </NavLink>
        ))}
      </nav>

      <aside className="hidden w-[30%] shrink-0 md:block">{rail}</aside>

      <main className="washi-grain flex-1 overflow-y-auto bg-washi text-ink">
        <div className="relative z-10 p-7">{children}</div>
      </main>
    </div>
  )
}
