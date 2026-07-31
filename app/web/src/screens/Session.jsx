import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'

function fmtPace(seconds) {
  if (!seconds) return '—'
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function Row({ label, value }) {
  return (
    <div className="flex items-baseline justify-between border-b border-ink/10 py-3">
      <span className="font-sans text-[13px] text-stone-2">{label}</span>
      <span className="font-mono text-[15px] text-ink">{value}</span>
    </div>
  )
}

export default function Session() {
  const [p, setP] = useState(null)
  const navigate = useNavigate()

  useEffect(() => { fetch('/api/session').then((r) => r.json()).then(setP) }, [])

  if (!p) return <Dojo rail={<RailMedia stem="session-route" />}>
    <p className="font-sans text-stone">…</p></Dojo>

  const isRest = p.session_type === 'rest'

  return (
    <Dojo rail={
      <RailMedia stem="session-route">
        <div className="font-serif text-lg text-washi">Riverside loop</div>
        {isRest && (
          <div className="mt-1 font-sans text-[11px] uppercase tracking-[.14em] text-washi/60">
            Rest day
          </div>
        )}
      </RailMedia>
    }>
      <div className="flex items-baseline gap-3">
        <button onClick={() => navigate('/')}
          className="font-sans text-[13px] text-stone-2">← Today</button>
        <span className="ml-auto font-sans text-[10px] font-semibold uppercase
                         tracking-[.16em] text-stone">
          Week <span className="font-mono">{p.week_n}</span>
        </span>
      </div>

      <h1 className="mt-2 font-serif text-2xl">
        {isRest ? 'Rest — no session today' : (
          <>
            <span className="capitalize">{p.session_type}</span>{' '}
            <span className="font-mono">{p.distance_km}</span> km
          </>
        )}
      </h1>

      <div className="mt-6">
        <Row label="Distance" value={p.distance_km ? `${p.distance_km} km` : '—'} />
        <Row label="Pace band" value={p.pace_band_s
          ? `${fmtPace(p.pace_band_s[0])}–${fmtPace(p.pace_band_s[1])} /km` : '—'} />
        <Row label="Heart rate cap" value={p.hr_cap ? `${p.hr_cap} bpm` : '—'} />
        <Row label="This week" value={`${p.week.km_so_far} / ${p.week.target_km} km`} />
      </div>

      {!isRest && (
        <button onClick={() => navigate('/brief')}
          className="mt-7 w-full rounded-md bg-ink py-3 font-sans text-xs
                     font-semibold uppercase tracking-[.08em] text-washi">
          Kurosawa speaks first
        </button>
      )}
    </Dojo>
  )
}
