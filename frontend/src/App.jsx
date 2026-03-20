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

const DECEASED_FIELDS = [
  { key: 'full_name',        span: 2 },
  { key: 'date_of_birth',    span: 1 },
  { key: 'date_of_death',    span: 1 },
  { key: 'ssn_last4',        span: 1 },
  { key: 'county',           span: 1 },
  { key: 'state',            span: 1 },
  { key: 'cause_of_death',   span: 2 },
  { key: 'surviving_spouse', span: 2 },
]

const FILER_FIELDS = [
  { key: 'filer_name',         span: 1 },
  { key: 'filer_relationship', span: 1 },
  { key: 'filer_address',      span: 2 },
]

function flattenParsed(data) {
  const d = data.deceased || {}
  const f = data.filer || {}
  const fields = {
    full_name:          d.full_name        ?? '',
    date_of_birth:      d.date_of_birth    ?? '',
    date_of_death:      d.date_of_death    ?? '',
    ssn_last4:          d.ssn_last4        ?? '',
    cause_of_death:     d.cause_of_death   ?? '',
    county:             d.county           ?? '',
    state:              d.state            ?? '',
    surviving_spouse:   d.surviving_spouse ?? '',
    filer_name:         f.name             ?? '',
    filer_relationship: f.relationship     ?? '',
    filer_address:      f.address          ?? '',
  }
  const rawMap = {
    full_name: d.full_name, date_of_birth: d.date_of_birth, date_of_death: d.date_of_death,
    ssn_last4: d.ssn_last4, cause_of_death: d.cause_of_death, county: d.county,
    state: d.state, surviving_spouse: d.surviving_spouse,
    filer_name: f.name, filer_relationship: f.relationship, filer_address: f.address,
  }
  const lowConf = new Set(Object.entries(rawMap).filter(([, v]) => v == null).map(([k]) => k))
  return { fields, lowConf }
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

function FieldInput({ fieldKey, fields, setFields, lowConf }) {
  const isLow = lowConf.has(fieldKey)
  return (
    <div>
      <label className="flex items-center gap-1 text-xs font-medium text-gray-400 uppercase tracking-widest mb-1">
        {toLabel(fieldKey)}
        {isLow && <span className="text-amber-400 text-sm leading-none" title="Low confidence — please verify">⚠</span>}
      </label>
      <input
        value={fields[fieldKey]}
        onChange={e => setFields(prev => ({ ...prev, [fieldKey]: e.target.value }))}
        className={`w-full px-3 py-2 text-sm rounded-lg border focus:outline-none focus:ring-2 focus:border-flamingo transition ${
          isLow
            ? 'border-yellow-400 bg-yellow-50 focus:ring-yellow-200'
            : 'border-gray-200 focus:ring-flamingo/30'
        }`}
      />
    </div>
  )
}

export default function App() {
  const [screen, setScreen]     = useState(1)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [fields, setFields]     = useState({})
  const [lowConf, setLowConf]   = useState(new Set())
  const [selected, setSelected] = useState(new Set())
  const [letters, setLetters]             = useState(null)
  const [expandedLetter, setExpandedLetter] = useState(null)
  const [dragging, setDragging]           = useState(false)

  async function processFile(file) {
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
      const { fields: parsed, lowConf: lc } = flattenParsed(data)
      setFields(parsed)
      setLowConf(lc)
      setScreen(2)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    processFile(e.dataTransfer.files[0])
  }

  async function handleDownloadPdf(institution) {
    const res = await fetch('/export-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ institution, fields }),
    })
    if (!res.ok) return
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${institution}_letter.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 100)
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
      setExpandedLetter(Object.keys(data.letters)[0] ?? null)
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
            {loading ? (
              <div className="flex flex-col items-center justify-center py-10 gap-3">
                <svg className="animate-spin w-8 h-8 text-flamingo" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                <p className="text-sm text-gray-500">Parsing certificate…</p>
              </div>
            ) : (
              <label
                className={`flex flex-col items-center justify-center w-full border-2 border-dashed rounded-xl py-10 cursor-pointer transition-colors ${
                  dragging ? 'border-flamingo bg-orange-50' : 'border-gray-200 hover:border-flamingo'
                }`}
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragEnter={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                <svg className="w-9 h-9 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span className="text-sm text-gray-600 mb-1">Drop death certificate here</span>
                <span className="text-sm font-medium text-flamingo">or click to browse</span>
                <span className="text-xs text-gray-400 mt-3">PDF or image · max 10 MB</span>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => processFile(e.target.files[0])}
                  className="hidden"
                />
              </label>
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
        <div className="max-w-2xl mx-auto">
          <div className="mb-6">
            <div className="w-10 h-10 bg-flamingo rounded-xl mb-4" />
            <h1 className="text-3xl font-semibold text-gray-900 mb-1">
              Review Extracted Fields
            </h1>
            <p className="text-sm text-gray-500">Fix any mistakes before generating letters.</p>
          </div>

          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Deceased</h2>
              <div className="grid grid-cols-2 gap-4">
                {DECEASED_FIELDS.map(({ key, span }) => (
                  <div key={key} className={span === 2 ? 'col-span-2' : ''}>
                    <FieldInput fieldKey={key} fields={fields} setFields={setFields} lowConf={lowConf} />
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Filer</h2>
              <div className="grid grid-cols-2 gap-4">
                {FILER_FIELDS.map(({ key, span }) => (
                  <div key={key} className={span === 2 ? 'col-span-2' : ''}>
                    <FieldInput fieldKey={key} fields={fields} setFields={setFields} lowConf={lowConf} />
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => setScreen(3)}
              className="w-full bg-flamingo hover:bg-[#d94a1a] text-white font-medium text-sm py-2.5 rounded-lg transition-colors cursor-pointer"
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
    <div className="min-h-screen bg-gray-50 flex">
      {/* Left panel — checklist */}
      <div className="w-80 flex-none bg-white border-r border-gray-100 flex flex-col">
        <div className="p-6 border-b border-gray-100">
          <div className="w-8 h-8 bg-flamingo rounded-lg mb-3" />
          <h1 className="text-lg font-semibold text-gray-900">Select Institutions</h1>
          <p className="text-xs text-gray-500 mt-0.5">Choose which organizations to notify.</p>
        </div>

        {/* Hours saved stat bar */}
        {selected.size > 0 && (
          <div className="px-6 py-3 border-b border-gray-100 bg-orange-50">
            <p className="text-xs font-medium text-gray-700 mb-1.5">
              Generating{' '}
              <span className="text-[color:var(--color-flamingo)] font-semibold">
                {selected.size} {selected.size === 1 ? 'letter' : 'letters'}
              </span>
              {' · '}
              Saving an estimated{' '}
              <span className="text-[color:var(--color-flamingo)] font-semibold">
                {selected.size * 1.5} hours
              </span>
            </p>
            <div className="h-2 bg-orange-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-[color:var(--color-flamingo)] rounded-full transition-all duration-300"
                style={{ width: `${(selected.size / ALL_KEYS.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4">
          <div
            className="flex items-center gap-2.5 px-2 py-2 rounded-lg cursor-pointer mb-2 border-b border-gray-100 pb-3"
            onClick={toggleAll}
          >
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              onClick={e => e.stopPropagation()}
              className="accent-flamingo w-4 h-4 flex-none"
            />
            <span className="text-sm font-medium text-gray-700">Select all</span>
          </div>

          <div className="space-y-4 mt-2">
            {Object.entries(grouped).map(([group, items]) => (
              <div key={group}>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1.5 px-2">
                  {group}
                </h3>
                <div className="space-y-0.5">
                  {items.map(({ key, label }) => (
                    <div
                      key={key}
                      className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-gray-700"
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(key)}
                        onChange={() => toggleOne(key)}
                        className="accent-flamingo w-4 h-4 flex-none"
                      />
                      <span className="text-sm">{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-100">
          <button
            onClick={handleGenerate}
            disabled={loading || selected.size === 0}
            className="w-full bg-flamingo hover:bg-[#d94a1a] disabled:bg-gray-100 disabled:text-gray-400 text-white font-medium text-sm py-2.5 rounded-lg transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? 'Generating…' : `Generate Letters (${selected.size})`}
          </button>
          {error && <p className="mt-2 text-xs text-red-500">Error: {error}</p>}
        </div>
      </div>

      {/* Right panel — letter preview */}
      <div className="flex-1 overflow-y-auto p-8">
        {!letters ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gray-100 mx-auto mb-4 flex items-center justify-center">
                <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-400">Select institutions and generate<br />letters to preview them here.</p>
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto space-y-3">
            {Object.entries(letters).map(([inst, html]) => {
              const isOpen = expandedLetter === inst
              return (
                <div key={inst} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                  <button
                    onClick={() => setExpandedLetter(isOpen ? null : inst)}
                    className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
                      {toLabel(inst)}
                    </span>
                    <div className="flex items-center gap-4">
                      {isOpen && (
                        <span
                          role="button"
                          onClick={e => { e.stopPropagation(); handleDownloadPdf(inst) }}
                          className="text-xs font-medium text-flamingo hover:text-[#d94a1a] transition-colors"
                        >
                          Download PDF
                        </span>
                      )}
                      <svg
                        className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </button>
                  {isOpen && (
                    <iframe
                      srcDoc={html}
                      title={`Letter — ${inst}`}
                      className="w-full border-t border-gray-100"
                      style={{ height: '860px', border: 'none', borderTop: '1px solid #f3f4f6' }}
                    />
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
