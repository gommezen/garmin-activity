/** Read an SSE stream from fetch. Calls onEvent(name, payload) per frame. */
export async function streamSSE(url, options, onEvent) {
  const res = await fetch(url, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop()

    for (const frame of frames) {
      let name = null
      let data = null
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) name = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (name && data !== null) onEvent(name, JSON.parse(data))
    }
  }
}
