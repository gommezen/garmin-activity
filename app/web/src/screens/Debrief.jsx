import { useEffect, useRef, useState } from 'react'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'
import Tile from '../components/Tile.jsx'
import { streamSSE } from '../lib/sse.js'

const FEELS = ['strong', 'good', 'flat', 'wrecked']

function fmtPace(seconds) {
  if (!seconds) return '—'
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function fmtDuration(seconds) {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  return `${m}:${String(seconds % 60).padStart(2, '0')}`
}

export default function Debrief() {
  const [verdict, setVerdict] = useState(null)
  const [text, setText] = useState('')
  const [streaming, setStreaming] = useState(true)
  const [debriefId, setDebriefId] = useState(null)
  const [feel, setFeel] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [asked, setAsked] = useState(false)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    streamSSE('/api/debrief/latest', {}, (name, payload) => {
      if (name === 'verdict') setVerdict(payload)
      else if (name === 'token') setText((t) => t + payload.t)
      else if (name === 'done') {
        setDebriefId(payload.debrief_id)
        if (payload.feel) setFeel(payload.feel)
        if (payload.followup_q) {
          setQuestion(payload.followup_q)
          setAnswer(payload.followup_a || '')
          setAsked(true)
        }
        setStreaming(false)
      }
    }).catch(() => setStreaming(false))
  }, [])

  async function recordFeel(value) {
    const res = await fetch(`/api/debrief/${debriefId}/feel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feel: value }),
    })
    if (res.ok) setFeel(value)
  }

  async function ask() {
    if (!question.trim() || asked) return
    try {
      await streamSSE(`/api/debrief/${debriefId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      }, (name, payload) => {
        if (name === 'token') setAnswer((a) => a + payload.t)
      })
      setAsked(true)
    } catch {
      // rejected (e.g. follow-up already used) — leave the control visible
    }
  }

  const rail = (
    <RailMedia stem="debrief-runner">
      <div className="font-sans text-[10px] font-semibold uppercase
                      tracking-[.16em] text-washi/60">The debrief</div>
      <p className="mt-2 font-serif italic leading-relaxed text-washi">
        {text}
        {streaming && <span className="ml-0.5 inline-block h-4 w-[7px]
                                       animate-pulse bg-gold align-[-2px]" />}
      </p>
      {answer && <p className="mt-4 border-t border-washi/20 pt-3 font-serif
                               italic leading-relaxed text-washi/90">{answer}</p>}
    </RailMedia>
  )

  if (verdict?.state === 'no_new_run') {
    return <Dojo rail={rail}>
      <h1 className="font-serif text-2xl">No run yet</h1>
      <p className="mt-3 font-sans text-[14px] text-stone-2">
        Nothing new since the last debrief. The road is still there.</p>
    </Dojo>
  }

  if (!verdict) return <Dojo rail={rail}>
    <p className="font-sans text-stone">…</p></Dojo>

  const r = verdict.run
  const band = verdict.vs_prescription?.pace
  const maxPace = Math.max(...(r.laps.length ? r.laps.map((l) => l.pace_s) : [1]))

  return (
    <Dojo rail={rail}>
      <div className="flex items-baseline gap-3">
        <span className="font-sans text-[10px] font-semibold uppercase
                         tracking-[.16em] text-stone">Session complete · <span className="font-mono">{r.date}</span></span>
        <span className="ml-auto">
          <span className="font-mono text-[30px] text-ink">{r.km}</span>
          <span className="ml-1 font-sans text-[10px] font-semibold uppercase
                           tracking-[.14em] text-stone">km</span>
        </span>
      </div>

      <div className="mt-5 flex gap-3">
        <Tile label="Time" value={fmtDuration(r.duration_s)} />
        <Tile label="Pace" value={fmtPace(r.pace_s)} />
        <Tile label="Avg HR" value={r.avg_hr ?? '—'} />
      </div>

      {r.laps.length > 0 && (
        <div className="mt-5 rounded-md border border-ink/10 bg-white/40 p-4">
          <div className="flex items-baseline">
            <span className="font-sans text-[10px] font-semibold uppercase
                             tracking-[.14em] text-stone">Pace per km</span>
            {band && <span className="ml-auto font-mono text-[10px] text-stone">
              {band.replace('_', ' ').toUpperCase()}</span>}
          </div>
          <div className="mt-3 flex h-14 items-end gap-1.5">
            {r.laps.map((l, i) => (
              <div key={i}
                className={`flex-1 rounded-t-sm ${
                  l.pace_s === maxPace ? 'bg-gold' : 'bg-stone-3'}`}
                title={`km ${i + 1} · ${fmtPace(l.pace_s)}`}
                style={{ height: `${(l.pace_s / maxPace) * 100}%` }} />
            ))}
          </div>
        </div>
      )}

      {debriefId && !feel && (
        <div className="mt-6">
          <div className="font-sans text-[10px] font-semibold uppercase
                          tracking-[.14em] text-stone">How did it feel?</div>
          <div className="mt-3 flex gap-2">
            {FEELS.map((f) => (
              <button key={f} onClick={() => recordFeel(f)}
                className="flex-1 rounded-md border border-ink/20 py-2 font-sans
                           text-[12px] capitalize text-ink hover:bg-ink/5">{f}</button>
            ))}
          </div>
        </div>
      )}
      {feel && <p className="mt-6 font-sans text-[13px] text-stone-2">
        Logged: <span className="text-ink">{feel}</span>. It shapes tomorrow's brief.</p>}

      {debriefId && !asked && (
        <div className="mt-6 flex gap-2">
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask()}
            placeholder="Ask him one thing…"
            className="flex-1 rounded-md border border-ink/20 bg-white/50 px-3
                       py-2 font-sans text-[13px] text-ink outline-none" />
          <button onClick={ask}
            className="rounded-md border border-gold px-4 font-sans text-[11px]
                       font-semibold uppercase tracking-[.14em] text-gold">Ask</button>
        </div>
      )}
    </Dojo>
  )
}
