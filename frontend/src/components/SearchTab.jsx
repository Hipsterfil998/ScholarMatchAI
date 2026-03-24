import { useState } from 'react'
import { parseCV, searchJobs, scoreJobs } from '../api.js'
import GraduationCapIcon from './GraduationCapIcon.jsx'
import { LOCATIONS, POSITION_TYPES } from '../constants.js'

const STEPS = [
  { key: 'parse',  label: 'Parsing CV…',                pct: 15 },
  { key: 'search', label: 'Searching job boards (~60s)…', pct: 50 },
  { key: 'score',  label: 'Scoring positions with AI…',  pct: 85 },
  { key: 'done',   label: 'Done!',                       pct: 100 },
]

const INPUT_CLS = 'w-full bg-[#0f0f12] border border-[#2e2e38] text-[#e8e8f0] placeholder-[#7a7a8f] focus:border-[#818cf8] focus:outline-none text-sm px-3 py-2'
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

      {/* Section header */}
      <div className="py-8">
        <p className="text-[10px] font-mono tracking-widest uppercase text-[#818cf8] mb-3">Academic job search</p>
        <h2 className="text-3xl font-bold text-[#e8e8f0] leading-tight">
          Find your next academic position
        </h2>
        <p className="mt-3 text-sm text-[#7a7a8f] leading-relaxed max-w-lg">
          Upload your CV, set your search parameters, and let AI find and score matching positions.
        </p>
      </div>

      {/* CV Upload */}
      <div
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onClick={() => document.getElementById('cv-input').click()}
        className={[
          'border border-dashed p-8 text-center transition-colors cursor-pointer bg-[#17171c] hover:bg-[#1c1c23]',
          dragging ? 'border-[#818cf8]/60' : 'border-[#2e2e38] hover:border-[#818cf8]/40',
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
      <div className="grid grid-cols-2 gap-px bg-[#2e2e38]">
        <div className="bg-[#0f0f12] p-4">
          <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1.5">Location</label>
          <select value={location} onChange={e => setLocation(e.target.value)} className={SELECT_CLS}>
            {LOCATIONS.map(loc => <option key={loc} value={loc}>{loc}</option>)}
          </select>
        </div>
        <div className="bg-[#0f0f12] p-4">
          <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1.5">Position type</label>
          <select value={positionType} onChange={e => setPositionType(e.target.value)} className={SELECT_CLS}>
            {POSITION_TYPES.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </div>

      {/* Min score */}
      <div className="bg-[#17171c] border border-[#2e2e38] p-4">
        <label className="block text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-3">
          Minimum match score
        </label>
        <div className="flex gap-1">
          {Array.from({ length: 10 }, (_, i) => {
            const val = (i + 1) * 10
            return (
              <button
                key={i}
                type="button"
                onClick={() => setMinScore(val)}
                title={`${val}`}
                className="transition-transform hover:scale-125 focus:outline-none"
                style={{ opacity: val <= minScore ? 1 : 0.25 }}
              >
                <GraduationCapIcon className="w-5 h-5 text-[#818cf8]" />
              </button>
            )
          })}
        </div>
        <p className="text-[10px] font-mono text-[#7a7a8f] mt-2">
          {minScore}/100 — {minScore <= 40 ? 'more results' : minScore >= 80 ? 'higher quality' : 'balanced'}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="border border-red-900 bg-red-950/20 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Progress */}
      {loading && (
        <div className="bg-[#17171c] border border-[#2e2e38] p-4 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-mono text-[#e8e8f0]">{currentStep.label}</span>
            <span className="font-mono text-[#818cf8] font-bold">{currentStep.pct}%</span>
          </div>
          <div className="w-full bg-[#0f0f12] border border-[#2e2e38] h-1">
            <div
              className="bg-[#818cf8] h-1 transition-all duration-500"
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
        className="w-full bg-[#818cf8] text-[#0f0f12] font-mono text-xs font-semibold tracking-widest uppercase py-3.5 px-6 hover:bg-[#a5b4fc] transition-colors disabled:bg-[#2e2e38] disabled:text-[#7a7a8f] disabled:cursor-not-allowed"
      >
        {loading ? 'Searching…' : 'Parse CV & Search Positions'}
      </button>

      {/* Info box */}
      <div className="flex flex-col gap-px bg-[#2e2e38] text-xs font-mono text-[#7a7a8f]">
        <p className="bg-[#17171c] px-4 py-2.5">Your CV is processed in memory and never stored on our servers.</p>
        <p className="bg-[#17171c] px-4 py-2.5">100% free — powered by Groq free API. No sign-up required.</p>
        <p className="bg-[#17171c] px-4 py-2.5">Searches Euraxess, ScholarshipDb, Nature Careers, mlscientist.com, and jobs.ac.uk.</p>
      </div>

    </div>
  )
}
