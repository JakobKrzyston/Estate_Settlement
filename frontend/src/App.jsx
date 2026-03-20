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
  const [screen, setScreen]     = useState(1)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [fields, setFields]     = useState({})
  const [selected, setSelected] = useState(new Set())
  const [letters, setLetters]   = useState(null)

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

  // ── Screen 1: Upload ────────────────────────────────────────────────────────
  if (screen === 1) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-6">
            <div className="w-10 h-10 bg-flamingo rounded-xl mb-4" />
            <h1 className="text-3xl font-semibold text-gray-900 mb-1">
              Upload Death Certificate
            </h1>
            <p className="text-sm text-gray-500">
              We'll extract the key details automatically.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
            <label className="flex flex-col items-center justify-center w-full border-2 border-dashed border-gray-200 rounded-xl py-10 cursor-pointer hover:border-flamingo transition-colors">
              <svg className="w-8 h-8 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm text-gray-400 mb-1">PDF, JPG, or PNG</span>
              <span className="text-sm font-medium text-flamingo">Click to upload</span>
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleUpload}
                disabled={loading}
                className="hidden"
              />
            </label>

            {loading && (
              <p className="mt-4 text-sm text-gray-400 flex items-center gap-2">
                <span className="inline-block animate-spin">⟳</span>
                Parsing certificate...
              </p>
            )}
            {error && <p className="mt-4 text-sm text-red-500">Error: {error}</p>}
          </div>
        </div>
      </div>
    )
  }

  // ── Screen 2: Review fields ─────────────────────────────────────────────────
  if (screen === 2) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-md mx-auto">
          <div className="mb-6">
            <div className="w-10 h-10 bg-flamingo rounded-xl mb-4" />
            <h1 className="text-3xl font-semibold text-gray-900 mb-1">
              Review Extracted Fields
            </h1>
            <p className="text-sm text-gray-500">Fix any mistakes before generating letters.</p>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
            <div className="space-y-4">
              {Object.entries(fields).map(([key, val]) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-400 uppercase tracking-widest mb-1">
                    {toLabel(key)}
                  </label>
                  <input
                    value={val}
                    onChange={e => setFields(prev => ({ ...prev, [key]: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-flamingo/30 focus:border-flamingo transition"
                  />
                </div>
              ))}
            </div>

            <button
              onClick={() => setScreen(3)}
              className="mt-6 w-full bg-flamingo hover:bg-[#d94a1a] text-white font-medium text-sm py-2.5 rounded-lg transition-colors cursor-pointer"
            >
              Looks good, continue →
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Screen 3: Select institutions + generate ────────────────────────────────
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
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-md mx-auto">
        <div className="mb-6">
          <div className="w-10 h-10 bg-flamingo rounded-xl mb-4" />
          <h1 className="text-3xl font-semibold text-gray-900 mb-1">Select Institutions</h1>
          <p className="text-sm text-gray-500">Choose which organizations to notify.</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <label className="flex items-center gap-2.5 text-sm font-medium text-gray-700 cursor-pointer mb-5 pb-4 border-b border-gray-100">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              className="accent-flamingo w-4 h-4"
            />
            Select all
          </label>

          <div className="space-y-5">
            {Object.entries(grouped).map(([group, items]) => (
              <div key={group}>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2.5">
                  {group}
                </h3>
                <div className="space-y-2.5">
                  {items.map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2.5 text-sm text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selected.has(key)}
                        onChange={() => toggleOne(key)}
                        className="accent-flamingo w-4 h-4"
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || selected.size === 0}
            className="mt-6 w-full bg-flamingo hover:bg-[#d94a1a] disabled:bg-gray-100 disabled:text-gray-400 text-white font-medium text-sm py-2.5 rounded-lg transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? 'Generating...' : `Generate Letters (${selected.size})`}
          </button>

          {error && <p className="mt-4 text-sm text-red-500">Error: {error}</p>}
        </div>

        {letters && (
          <div className="mt-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Generated Letters</h2>
            {Object.entries(letters).map(([inst, text]) => (
              <div key={inst} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">{toLabel(inst)}</h3>
                <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono bg-gray-50 rounded-lg p-4">
                  {text}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
