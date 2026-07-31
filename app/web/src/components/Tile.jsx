/** A stat on washi paper. Numbers are always mono. */
export default function Tile({ label, value, unit }) {
  return (
    <div className="flex flex-1 flex-col gap-2 rounded-md border border-ink/10
                    bg-white/40 px-3 py-3">
      <span className="font-sans text-[10px] font-semibold uppercase tracking-[.14em]
                       text-stone">{label}</span>
      <span className="font-mono text-[22px] leading-none text-ink">
        {value}{unit && <span className="ml-1 text-[11px] text-stone">{unit}</span>}
      </span>
    </div>
  )
}
