import { useState, useRef } from 'react'
import { parseCV, searchJobs, scoreJobs } from '../api.js'
import { LOCATIONS, POSITION_TYPES } from '../constants.js'

const STEPS = [
  { key: 'parse',  label: 'Parsing CV…',               pct: 15 },
  { key: 'search', label: 'Searching job boards (~60s)…', pct: 50 },
  { key: 'score',  label: 'Scoring positions with AI…',  pct: 85 },
  { key: 'done',   label: 'Done!',                       pct: 100 },
]

export default function SearchTab({ onDone }) {
  const [cvFile, setCvFile] = useState(null)
  const [field, setField] = useState('')
  const [location, setLocation] = useState('Europe (all)')
  const [positionType, setPositionType] = useState('phd')
  const [minScore, setMinScore] = useState(60)

  const [loading, setLoading] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [error, setError] = useState('')

  const dropRef = useRef(null)

  // ── Drag & drop ────────────────────────────────────────────────────────
  function handleDrop(e) {
    e.preventDefault()
    dropRef.current?.classList.remove('border-blue-400', 'bg-blue-50')
    const file = e.dataTransfer.files[0]
    if (file) setCvFile(file)
  }

  function handleDragOver(e) {
    e.preventDefault()
    dropRef.current?.classList.add('border-blue-400', 'bg-blue-50')
  }

  function handleDragLeave() {
    dropRef.current?.classList.remove('border-blue-400', 'bg-blue-50')
  }

  // ── Search pipeline ────────────────────────────────────────────────────
  async function handleSearch() {
    if (!cvFile) { setError('Please upload a CV file.'); return }
    if (!field.trim()) { setError('Please enter a research field.'); return }

    setError('')
    setLoading(true)
    setStepIdx(0)

    try {
      // Step 1 — parse CV
      const { profile, profile_text } = await parseCV(cvFile)

      // Step 2 — search job boards
      setStepIdx(1)
      const { jobs } = await searchJobs({ field: field.trim(), location, positionType })

      if (!jobs || jobs.length === 0) {
        setError('No positions found. Try a broader field or location.')
        setLoading(false)
        return
      }

      // Step 3 — score with AI
      setStepIdx(2)
      const { scored_jobs } = await scoreJobs({ jobs, profileText: profile_text })

      setStepIdx(3)
      onDone({ profile, profileText: profile_text, scoredJobs: scored_jobs })
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Unknown error'
      setError(`Error: ${msg}`)
    } finally {
      setLoading(false)
      setStepIdx(0)
    }
  }

  const currentStep = STEPS[stepIdx]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Find your next academic position</h2>
        <p className="mt-1 text-sm text-gray-500">
          Upload your CV, set your search parameters, and let AI find and score matching positions.
        </p>
      </div>

      {/* CV Upload */}
      <div
        ref={dropRef}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center transition-colors cursor-pointer hover:border-blue-400 hover:bg-blue-50"
        onClick={() => document.getElementById('cv-input').click()}
      >
        <input
          id="cv-input"
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={e => setCvFile(e.target.files[0] || null)}
        />
        {cvFile ? (
          <div className="space-y-1">
            <p className="text-2xl">📄</p>
            <p className="font-medium text-gray-900">{cvFile.name}</p>
            <p className="text-xs text-gray-400">{(cvFile.size / 1024).toFixed(0)} KB · click to change</p>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-2xl text-gray-400">⬆️</p>
            <p className="font-medium text-gray-700">Drop your CV here or click to browse</p>
            <p className="text-xs text-gray-400">PDF, DOCX, or TXT</p>
          </div>
        )}
      </div>

      {/* Research field */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Research field <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={field}
          onChange={e => setField(e.target.value)}
          placeholder="e.g. machine learning, computational neuroscience, molecular biology"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Location + Position type */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <select
            value={location}
            onChange={e => setLocation(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {LOCATIONS.map(loc => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Position type</label>
          <select
            value={positionType}
            onChange={e => setPositionType(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {POSITION_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Min score */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Minimum match score: <span className="font-bold text-blue-600">{minScore}</span>
        </label>
        <input
          type="range"
          min={30} max={90} step={5}
          value={minScore}
          onChange={e => setMinScore(Number(e.target.value))}
          className="w-full accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-0.5">
          <span>30 — more results</span>
          <span>90 — higher quality</span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Progress */}
      {loading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-700 font-medium">{currentStep.label}</span>
            <span className="text-gray-400">{currentStep.pct}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${currentStep.pct}%` }}
            />
          </div>
          <p className="text-xs text-gray-400">
            The job board search can take up to 90 seconds — please wait.
          </p>
        </div>
      )}

      {/* Search button */}
      <button
        onClick={handleSearch}
        disabled={loading}
        className="w-full py-3 px-6 rounded-xl bg-blue-600 text-white font-semibold text-sm
          hover:bg-blue-700 active:bg-blue-800 disabled:bg-gray-300 disabled:cursor-not-allowed
          transition-colors shadow-sm"
      >
        {loading ? 'Searching…' : '🔍 Parse CV & Search Positions'}
      </button>

      {/* Info box */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 text-xs text-gray-500 space-y-1">
        <p>🔒 Your CV is processed in memory and never stored on our servers.</p>
        <p>🆓 100% free — powered by Groq's free API tier. No sign-up required.</p>
        <p>🌐 Searches Euraxess, ScholarshipDb, Nature Careers, mlscientist.com, and jobs.ac.uk (UK).</p>
      </div>
    </div>
  )
}
