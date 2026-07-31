import { useEffect, useState } from 'react'

/**
 * The sensei rail's art. Plays a Higgsfield loop when one exists for this stem,
 * otherwise shows the poster with a slow ken-burns drift. Honours reduced motion.
 */
export default function RailMedia({ stem, children }) {
  const [hasVideo, setHasVideo] = useState(false)
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (reduced) return
    fetch(`/art/${stem}.webm`, { method: 'HEAD' })
      .then((r) => setHasVideo(r.ok))
      .catch(() => setHasVideo(false))
  }, [stem, reduced])

  return (
    <div className="relative h-full overflow-hidden bg-ink-2">
      {hasVideo ? (
        <video
          className="absolute inset-0 h-full w-full object-cover"
          src={`/art/${stem}.webm`}
          poster={`/art/${stem}.jpg`}
          autoPlay loop muted playsInline
        />
      ) : (
        <img
          className={`absolute inset-0 h-full w-full object-cover ${reduced ? '' : 'kenburns'}`}
          src={`/art/${stem}.jpg`}
          alt=""
        />
      )}
      <div className="absolute inset-x-0 bottom-0 p-5"
           style={{ background: 'linear-gradient(180deg,transparent,rgba(12,11,10,.88) 42%)' }}>
        {children}
      </div>
    </div>
  )
}
