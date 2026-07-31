import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Dojo from '../components/Dojo.jsx'
import RailMedia from '../components/RailMedia.jsx'
import { streamSSE } from '../lib/sse.js'

export default function Brief() {
  const [prescription, setPrescription] = useState(null)
  const [text, setText] = useState('')
  const [streaming, setStreaming] = useState(true)
  const navigate = useNavigate()
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return          // StrictMode double-mount guard
    started.current = true
    streamSSE('/api/brief', {}, (name, payload) => {
      if (name === 'prescription') setPrescription(payload)
      else if (name === 'token') setText((t) => t + payload.t)
      else if (name === 'done') setStreaming(false)
    }).catch(() => setStreaming(false))
  }, [])

  return (
    <Dojo rail={
      <RailMedia stem="brief-sensei">
        <div className="font-sans text-[10px] font-semibold uppercase
                        tracking-[.16em] text-washi/60">The brief · 20 seconds</div>
        <p className="mt-2 font-serif italic leading-relaxed text-washi">
          {text}
          {streaming && <span className="ml-0.5 inline-block h-4 w-[7px]
                                         animate-pulse bg-gold align-[-2px]" />}
        </p>
      </RailMedia>
    }>
      <h1 className="font-serif text-2xl">Before you go</h1>

      {prescription && (
        <div className="mt-6 space-y-3">
          {prescription.evidence.map((e, i) => (
            <div key={i} className="flex items-baseline justify-between
                                    rounded-md border border-ink/10 bg-white/40 px-4 py-3">
              <span className="font-sans text-[10px] font-semibold uppercase
                               tracking-[.14em] text-stone">{e.label}</span>
              <span className="font-sans text-[13px] text-ink">{e.value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-7 flex gap-3">
        <button onClick={() => navigate('/debrief')}
          className="flex-1 rounded-md bg-ink py-3 font-sans text-xs font-semibold
                     uppercase tracking-[.08em] text-washi">Begin the run</button>
        <button onClick={() => navigate('/')}
          className="flex-1 rounded-md border border-ink/20 py-3 font-sans text-xs
                     font-semibold uppercase tracking-[.08em] text-ink">Skip</button>
      </div>
    </Dojo>
  )
}
