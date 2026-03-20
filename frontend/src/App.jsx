import { useState } from 'react'

const INSTITUTIONS = [
  { group: 'Government',           key: 'ssa',           label: 'Social Security Administration' },
  { group: 'Government',           key: 'medicare',      label: 'Medicare' },
  { group: 'Government',           key: 'irs',           label: 'IRS' },
  { group: 'Banks & Finance',      key: 'bank',          label: 'Bank' },
  { group: 'Banks & Finance',      key: 'credit_union',  label: 'Credit Union' },
  { group: 'Banks & Finance',      key: 'brokerage',     label: 'Brokerage' },
  { group: 'Banks & Finance',      key: 'mortgage',      label: 'Mortgage Lender' },
  { group: 'Banks & Finance',      key: 'life_insurance',label: 'Life Insurance' },
  { group: 'Banks & Finance',      key: 'pension',       label: 'Pension / Retirement' },
  { group: 'Banks & Finance',      key: 'usaa',          label: 'USAA' },
  { group: 'Subscriptions',        key: 'amazon',        label: 'Amazon' },
  { group: 'Subscriptions',        key: 'linkedin',      label: 'LinkedIn' },
  { group: 'Subscriptions',        key: 'subscriptions', label: 'Other Subscriptions' },
  { group: 'Utilities & Services', key: 'telecom',       label: 'Phone / Telecom' },
  { group: 'Utilities & Services', key: 'utility',       label: 'Utility Companies' },
]

const ALL_KEYS = INSTITUTIONS.map(i => i.key)

function flattenParsed(data) {
  const d = data.deceased || {}
  const f = data.filer || {}
  return {
    full_name:          d.full_name        || '',
    date_of_birth:      d.date_of_birth    || '',
    date_of_death:      d.date_of_death    || '',
    ssn_last4:          d.ssn_last4        || '',
    cause_of_death:     d.cause_of_death   || '',
    county:             d.county           || '',
    state:              d.state            || '',
    surviving_spouse:   d.surviving_spouse || '',
    filer_name:         f.name             || '',
    filer_relationship: f.relationship     || '',
    filer_address:      f.address          || '',
  }
}

function toLabel(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function groupBy(arr, key) {
  return arr.reduce((acc, item) => {
    ;(acc[item[key]] = acc[item[key]] || []).push(item)
    return acc
  }, {})
}

export default function App() {
  const [screen, setScreen]   = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [fields, setFields]   = useState({})
  const [selected, setSelected] = useState(new Set())
  const [letters, setLetters] = useState(null)

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setError(null)
    setLoading(true)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('/parse', { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || res.statusText)
      }
      const data = await res.json()
      setFields(flattenParsed(data))
      setScreen(2)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields, institutions: [...selected] }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || res.statusText)
      }
      const data = await res.json()
      setLetters(data.letters)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const s = { padding: '2rem', fontFamily: 'sans-serif', maxWidth: 640 }

  if (screen === 1) {
    return (
      <div style={s}>
        <h1>Death Certificate Parser</h1>
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleUpload}
          disabled={loading}
        />
        {loading && (
          <p style={{ color: '#666' }}>
            <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
            {' '}Parsing certificate...
          </p>
        )}
        {error && <p style={{ color: 'red' }}>Error: {error}</p>}
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (screen === 2) {
    return (
      <div style={s}>
        <h1>Review Extracted Fields</h1>
        <p style={{ color: '#666' }}>Fix any mistakes before generating letters.</p>
        {Object.entries(fields).map(([key, val]) => (
          <div key={key} style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 2 }}>
              {toLabel(key)}
            </label>
            <input
              value={val}
              onChange={e => setFields(prev => ({ ...prev, [key]: e.target.value }))}
              style={{ width: '100%', padding: '6px 8px', fontSize: 14, boxSizing: 'border-box' }}
            />
          </div>
        ))}
        <button
          onClick={() => setScreen(3)}
          style={{ marginTop: '1rem', padding: '8px 20px', fontSize: 15, cursor: 'pointer' }}
        >
          Looks good, continue →
        </button>
      </div>
    )
  }

  // Screen 3
  const grouped = groupBy(INSTITUTIONS, 'group')
  const allSelected = ALL_KEYS.every(k => selected.has(k))

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(ALL_KEYS))
  }

  function toggleOne(key) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  return (
    <div style={s}>
      <h1>Select Institutions</h1>
      <label style={{ cursor: 'pointer', fontWeight: 'bold' }}>
        <input type="checkbox" checked={allSelected} onChange={toggleAll} style={{ marginRight: 6 }} />
        Select all
      </label>

      {Object.entries(grouped).map(([group, items]) => (
        <div key={group} style={{ marginTop: '1.5rem' }}>
          <h3 style={{ margin: '0 0 0.5rem' }}>{group}</h3>
          {items.map(({ key, label }) => (
            <label key={key} style={{ display: 'block', cursor: 'pointer', marginBottom: 4 }}>
              <input
                type="checkbox"
                checked={selected.has(key)}
                onChange={() => toggleOne(key)}
                style={{ marginRight: 6 }}
              />
              {label}
            </label>
          ))}
        </div>
      ))}

      <button
        onClick={handleGenerate}
        disabled={loading || selected.size === 0}
        style={{ marginTop: '1.5rem', padding: '8px 20px', fontSize: 15, cursor: 'pointer' }}
      >
        {loading ? 'Generating...' : `Generate Letters (${selected.size})`}
      </button>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {letters && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Generated Letters</h2>
          {Object.entries(letters).map(([inst, text]) => (
            <div key={inst} style={{ marginBottom: '2rem' }}>
              <h3>{toLabel(inst)}</h3>
              <pre style={{ background: '#f5f5f5', padding: '1rem', whiteSpace: 'pre-wrap' }}>{text}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
