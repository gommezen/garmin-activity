import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'
import Tile from '../components/Tile.jsx'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function fmtPace(seconds) {
  if (!seconds) return '—'
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

export default function Home() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/today')
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  if (error) return <Dojo rail={<RailMedia stem="home-sensei" />}>
    <p className="font-sans text-crimson">{error}</p></Dojo>
  if (!data) return <Dojo rail={<RailMedia stem="home-sensei" />}>
    <p className="font-sans text-stone">…</p></Dojo>

  const p = data.prescription
  const maxKm = Math.max(...data.last_7_days.map((d) => d.km), 1)
  const isRest = p.session_type === 'rest'

  return (
    <Dojo rail={
      <RailMedia stem="home-sensei">
        <div className="font-sans text-[10px] font-semibold uppercase
                        tracking-[.16em] text-washi/60">Today's word</div>
        <p className="mt-2 font-serif italic leading-relaxed text-washi">
          {data.word || 'Slow enough to speak. Anything faster is borrowing from tomorrow.'}
        </p>
      </RailMedia>
    }>
      <div className="flex items-baseline gap-3">
        <span className="font-sans text-[10px] font-semibold uppercase
                         tracking-[.16em] text-stone">
          {DAYS[new Date(data.date).getDay() === 0 ? 6 : new Date(data.date).getDay() - 1]}
          {' · '}Week {p.week_n}
        </span>
        <span className="ml-auto font-mono text-[11px] text-stone-2">
          {data.streak}-DAY STREAK
        </span>
      </div>

      <h1 className="mt-2 font-serif text-3xl capitalize">
        {isRest ? 'Rest' : `${p.session_type} ${p.distance_km} km`}
      </h1>

      <div className="mt-6 flex gap-3">
        <Tile label="This week" value={data.week.km_so_far} unit="km" />
        <Tile label="Target" value={data.week.target_km} unit="km" />
        <Tile label="Pace band" value={p.pace_band_s
          ? `${fmtPace(p.pace_band_s[0])}–${fmtPace(p.pace_band_s[1])}` : '—'} />
        <Tile label="HR cap" value={p.hr_cap ?? '—'} />
      </div>

      <div className="mt-6 rounded-md border border-ink/10 bg-white/40 p-4">
        <div className="font-sans text-[10px] font-semibold uppercase
                        tracking-[.14em] text-stone">Last 7 days</div>
        <div className="mt-3 flex h-16 items-end gap-2">
          {data.last_7_days.map((d) => (
            <div key={d.date} className="flex-1 rounded-t-sm"
              title={`${d.date} · ${d.km} km`}
              style={{
                height: `${Math.max((d.km / maxKm) * 100, 3)}%`,
                background: d.km > 0 ? 'var(--gold)' : 'var(--stone-3)',
              }} />
          ))}
        </div>
      </div>

      <button onClick={() => navigate(isRest ? '/debrief' : '/session')}
        className="mt-6 w-full rounded-md bg-ink py-3 font-sans text-xs
                   font-semibold uppercase tracking-[.08em] text-washi">
        {isRest ? 'See the last debrief' : 'Start session'}
      </button>
    </Dojo>
  )
}
