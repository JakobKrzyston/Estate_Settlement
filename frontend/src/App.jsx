import { useState } from 'react'

function App() {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleChange(e) {
    const file = e.target.files[0]
    if (!file) return

    setError(null)
    setResult(null)
    setLoading(true)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('/parse', { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || res.statusText)
      }
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Death Certificate Parser</h1>
      <input
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        onChange={handleChange}
        disabled={loading}
      />
      {loading && <p>Parsing...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  )
}

export default App
