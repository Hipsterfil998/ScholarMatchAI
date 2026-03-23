import { useState } from 'react'
import { parseCV, searchJobs, scoreJobs } from '../api.js'
import { LOCATIONS, POSITION_TYPES } from '../constants.js'

const STEPS = [
  { key: 'parse',  label: 'Parsing CV…',                pct: 15 },
  { key: 'search', label: 'Searching job boards (~60s)…', pct: 50 },
  { key: 'score',  label: 'Scoring positions with AI…',  pct: 85 },
  { key: 'done',   label: 'Done!',                       pct: 100 },
]

const INPUT_CLS = 'w-full bg-[#0f0f12] border border-[#2e2e38] text-[#e8e8f0] placeholder-[#7a7a8f] focus:border-[#818cf8] focus:outline-none text-sm  px-3 py-2'
const SELECT_CLS = INPUT_CLS

export default function SearchTab({ onDone }) {
  const [cvFile, setCvFile] = useState(null)
  const [field, setField] = useState('')
  const [location, setLocation] = useState('Europe (all)')
  const [positionType, setPositionType] = useState('phd')
  const [minScore, setMinScore] = useState(60)
  const [loading, setLoading] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) setCvFile(file)
  }

  function handleDragOver(e) {
    e.preventDefault()
    setDragging(true)
  }

  function handleDragLeave() {
    setDragging(false)
  }

  async function handleSearch() {
    if (!cvFile) { setError('Please upload a CV file.'); return }
    if (!field.trim()) { setError('Please enter a research field.'); return }
    setError('')
    setLoading(true)
    setStepIdx(0)
    try {
      const { profile, profile_text } = await parseCV(cvFile)
      setStepIdx(1)
      const { jobs } = await searchJobs({ field: field.trim(), location, positionType })
      if (!jobs || jobs.length === 0) {
        setError('No positions found. Try a broader field or location.')
        setLoading(false)
        return
      }
      setStepIdx(2)
      const { scored_jobs } = await scoreJobs({ jobs, profileText: profile_text })
      setStepIdx(3)
      onDone({ profile, profileText: profile_text, scoredJobs: scored_jobs })
    } catch (err) {
      setError('Error: ' + (err?.response?.data?.detail || err.message || 'Unknown error'))
    } finally {
      setLoading(false)
      setStepIdx(0)
    }
  }

  const currentStep = STEPS[stepIdx]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Hero */}
      <div className="py-6">
        <h2 className="font-mono text-2xl font-semibold tracking-tight text-[#e8e8f0]">
          Find your next academic position
        </h2>
        <p className="mt-2 text-sm  text-[#7a7a8f]">
          Upload your CV, set your search parameters, and let AI find and score matching positions.
        </p>
      </div>

      {/* CV Upload */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => document.getElementById('cv-input').click()}
        className={[
          'border border-dashed p-8 text-center transition-colors cursor-pointer',
          dragging
            ? 'border-[#818cf8]/60'
            : 'border-[#2e2e38] hover:border-[#818cf8]/60',
        ].join(' ')}
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
            <p className="font-mono text-sm font-medium text-[#e8e8f0]">{cvFile.name}</p>
            <p className="text-xs font-mono text-[#7a7a8f]">{(cvFile.size / 1024).toFixed(0)} KB · click to change</p>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="font-mono text-sm font-medium text-[#7a7a8f]">Drop your CV here or click to browse</p>
            <p className="text-xs font-mono text-[#7a7a8f]/60">PDF, DOCX, or TXT</p>
          </div>
        )}
      </div>

      {/* Research field */}
      <div>
        <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1.5">
          Research field <span className="text-red-500 normal-case">*</span>
        </label>
        <input
          type="text"
          value={field}
          onChange={e => setField(e.target.value)}
          placeholder="e.g. machine learning, computational neuroscience, molecular biology"
          className={INPUT_CLS}
        />
      </div>

      {/* Location + Position type */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1.5">Location</label>
          <select value={location} onChange={e => setLocation(e.target.value)} className={SELECT_CLS}>
            {LOCATIONS.map(loc => <option key={loc} value={loc}>{loc}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1.5">Position type</label>
          <select value={positionType} onChange={e => setPositionType(e.target.value)} className={SELECT_CLS}>
            {POSITION_TYPES.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </div>

      {/* Min score */}
      <div>
        <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1.5">
          Minimum match score: <span className="font-bold text-[#818cf8] normal-case">{minScore}</span>
        </label>
        <input
          type="range"
          min={30} max={90} step={5}
          value={minScore}
          onChange={e => setMinScore(Number(e.target.value))}
          className="w-full accent-[#818cf8]"
        />
        <div className="flex justify-between text-[10px] font-mono text-[#7a7a8f] mt-0.5">
          <span>30 — more results</span>
          <span>90 — higher quality</span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="border border-red-900 p-3 text-sm  text-red-400">
          {error}
        </div>
      )}

      {/* Progress */}
      {loading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-mono text-[#e8e8f0]">{currentStep.label}</span>
            <span className="font-mono text-[#7a7a8f]">{currentStep.pct}%</span>
          </div>
          <div className="w-full bg-[#17171c] border border-[#2e2e38] h-1.5">
            <div
              className="bg-[#818cf8] h-1.5 transition-all duration-500"
              style={{ width: `${currentStep.pct}%` }}
            />
          </div>
          <p className="text-[10px] font-mono text-[#7a7a8f]">The job board search can take up to 90 seconds — please wait.</p>
        </div>
      )}

      {/* Search button */}
      <button
        onClick={handleSearch}
        disabled={loading}
        className="w-full border border-[#818cf8] text-[#818cf8] font-mono text-xs tracking-widest uppercase py-3 px-6 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors disabled:border-[#2e2e38] disabled:text-[#7a7a8f] disabled:cursor-not-allowed"
      >
        {loading ? 'Searching…' : 'Parse CV & Search Positions'}
      </button>

      {/* Info box */}
      <div className="border border-[#2e2e38] p-4 text-xs  text-[#7a7a8f] space-y-1">
        <p>Your CV is processed in memory and never stored on our servers.</p>
        <p>100% free — powered by Groq free API. No sign-up required.</p>
        <p>Searches Euraxess, ScholarshipDb, Nature Careers, mlscientist.com, and jobs.ac.uk (UK).</p>
      </div>
    </div>
  )
}
