import { useState } from 'react'
import { prepareApplication, regenerateLetter } from '../api.js'
import { REC_CONFIG } from '../constants.js'
import GraduationCapIcon from './GraduationCapIcon.jsx'

const SECTION_LABEL = 'text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f]'
const INPUT_CLS = 'w-full bg-[#0f0f12] border border-[#2e2e38] text-[#e8e8f0] placeholder-[#7a7a8f] focus:border-[#818cf8] focus:outline-none text-sm  px-3 py-2'

function JobDetails({ job }) {
  const match = job.match || {}
  const score = match.match_score || 0
  const filled = Math.round(score / 10)
  const rec = match.recommendation || ''
  const recCfg = REC_CONFIG[rec] || {}
  const institution = job.institution || job.company || ''

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-mono font-semibold text-[#e8e8f0] text-base leading-tight">{job.title}</h3>
        <p className="text-sm  text-[#7a7a8f] mt-0.5">
          {institution}{institution && job.location ? ' · ' : ''}{job.location}
        </p>
        {job.url && (
          <a href={job.url} target="_blank" rel="noreferrer"
            className="text-xs font-mono text-[#818cf8] link-underline break-all">
            {job.url}
          </a>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        {job.type && (
          <div className="bg-[#0f0f12] border border-[#2e2e38] p-2">
            <p className="font-mono text-[#7a7a8f]">Type</p>
            <p className="font-mono font-medium text-[#e8e8f0] capitalize">{job.type}</p>
          </div>
        )}
        {job.deadline && (
          <div className="bg-[#0f0f12] border border-[#2e2e38] p-2">
            <p className="font-mono text-[#7a7a8f]">Deadline</p>
            <p className="font-mono font-medium text-[#e8e8f0]">{job.deadline}</p>
          </div>
        )}
        {job.source && (
          <div className="bg-[#0f0f12] border border-[#2e2e38] p-2">
            <p className="font-mono text-[#7a7a8f]">Source</p>
            <p className="font-mono font-medium text-[#e8e8f0]">{job.source}</p>
          </div>
        )}
        {job.freshness && (
          <div className="bg-[#0f0f12] border border-[#2e2e38] p-2">
            <p className="font-mono text-[#7a7a8f]">Freshness</p>
            <p className="font-mono font-medium text-[#e8e8f0]">{job.freshness}</p>
          </div>
        )}
      </div>

      <div className="border border-[#2e2e38] p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-mono text-[#e8e8f0]">Match score</p>
          <span className="font-mono font-bold text-[#e8e8f0]">{score}/100</span>
        </div>
        <div className="flex items-center gap-px">
          {Array.from({ length: 10 }, (_, i) => (
            <GraduationCapIcon
              key={i}
              className={`w-4 h-4 ${i < filled ? 'text-[#818cf8]' : 'text-[#2e2e38]'}`}
            />
          ))}
        </div>
        {rec && (
          <span className={`inline-flex text-xs px-2.5 py-1 border font-mono ${recCfg.color || ''}`}>
            {recCfg.icon} Recommendation: {recCfg.label}
          </span>
        )}
        {match.why_good_fit && (
          <div>
            <p className={`${SECTION_LABEL} mb-0.5`}>Why a good fit</p>
            <p className="text-sm  text-[#7a7a8f]">{match.why_good_fit}</p>
          </div>
        )}
        {match.concerns && (
          <div>
            <p className={`${SECTION_LABEL} mb-0.5`}>Concerns</p>
            <p className="text-sm  text-[#7a7a8f]">{match.concerns}</p>
          </div>
        )}
        {(match.matching_areas || []).length > 0 && (
          <div>
            <p className={`${SECTION_LABEL} mb-0.5`}>Matching areas</p>
            <ul className="space-y-0.5">
              {match.matching_areas.map((a, i) => (
                <li key={i} className="text-xs  text-[#7a7a8f]">✓ {a}</li>
              ))}
            </ul>
          </div>
        )}
        {(match.missing_requirements || []).length > 0 && (
          <div>
            <p className={`${SECTION_LABEL} mb-0.5`}>Missing requirements</p>
            <ul className="space-y-0.5">
              {match.missing_requirements.map((r, i) => (
                <li key={i} className="text-xs  text-[#7a7a8f]">⚠ {r}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {job.description && (
        <details className="text-xs">
          <summary className="cursor-pointer font-mono text-[#7a7a8f] hover:text-[#e8e8f0] tracking-wide">
            Full description
          </summary>
          <p className="mt-2  text-[#7a7a8f] whitespace-pre-wrap leading-relaxed">{job.description}</p>
        </details>
      )}
    </div>
  )
}

function HintsPanel({ hints }) {
  if (!hints) return (
    <p className="text-sm  text-[#7a7a8f] italic">Load a position to see CV tailoring hints.</p>
  )

  return (
    <div className="space-y-4">
      {hints.headline_suggestion && (
        <div>
          <p className={`${SECTION_LABEL} mb-1`}>Profile summary tweak</p>
          <blockquote className="border-l border-[#818cf8] pl-3 text-sm  text-[#7a7a8f] italic">
            {hints.headline_suggestion}
          </blockquote>
        </div>
      )}
      {hints.research_alignment && (
        <div>
          <p className={`${SECTION_LABEL} mb-1`}>Research alignment</p>
          <blockquote className="border-l border-[#818cf8] pl-3 text-sm  text-[#7a7a8f] italic">
            {hints.research_alignment}
          </blockquote>
        </div>
      )}
      {(hints.skills_to_highlight || []).length > 0 && (
        <div>
          <p className={`${SECTION_LABEL} mb-1`}>Skills to highlight</p>
          <ul className="space-y-1">
            {hints.skills_to_highlight.map((s, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm  text-[#7a7a8f]">
                <input type="checkbox" className="mt-0.5 accent-[#818cf8]" readOnly />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(hints.experience_to_emphasize || []).length > 0 && (
        <div>
          <p className={`${SECTION_LABEL} mb-1`}>Experience to highlight</p>
          <ul className="space-y-1">
            {hints.experience_to_emphasize.map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm  text-[#7a7a8f]">
                <input type="checkbox" className="mt-0.5 accent-[#818cf8]" readOnly />
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(hints.keywords_to_add || []).length > 0 && (
        <div>
          <p className={`${SECTION_LABEL} mb-1`}>Keywords to add</p>
          <div className="flex flex-wrap gap-1">
            {hints.keywords_to_add.map((k, i) => (
              <code key={i} className="text-xs font-mono text-[#7a7a8f] border border-[#2e2e38] px-1.5 py-0.5">
                {k}
              </code>
            ))}
          </div>
        </div>
      )}
      {(hints.suggested_order || []).length > 0 && (
        <div>
          <p className={`${SECTION_LABEL} mb-1`}>Suggested section order</p>
          <ol className="space-y-0.5 list-decimal list-inside">
            {hints.suggested_order.map((s, i) => (
              <li key={i} className="text-sm  text-[#7a7a8f]">{s}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

export default function ReviewTab({
  scoredJobs,
  profileText,
  currentJobIdx,
  setCurrentJobIdx,
  currentHints,
  setCurrentHints,
  coverLetter,
  setCoverLetter,
  onApprove,
}) {
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingRegen, setLoadingRegen] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const job = currentJobIdx >= 0 ? scoredJobs[currentJobIdx] : null
  const institution = job ? (job.institution || job.company || '') : ''

  const positionChoices = scoredJobs.map((j, i) => ({
    label: `[${j.match?.match_score || 0}] ${j.institution || j.company || 'Unknown'} — ${j.title || 'Unknown'}`,
    idx: i,
  }))

  async function handleLoad(idx) {
    setCurrentJobIdx(idx)
    setCurrentHints(null)
    setCoverLetter('')
    setStatus('')
    setError('')
    setLoading(true)
    try {
      const { hints, cover_letter } = await prepareApplication({ job: scoredJobs[idx], profileText })
      setCurrentHints(hints)
      setCoverLetter(cover_letter)
      setStatus(`Loaded: ${scoredJobs[idx].title} @ ${scoredJobs[idx].institution || 'Unknown'}`)
    } catch (err) {
      setError('Failed to load position: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  async function handleRegen() {
    if (!job) return
    setLoadingRegen(true)
    try {
      const { cover_letter } = await regenerateLetter({ job, profileText })
      setCoverLetter(cover_letter)
    } catch (err) {
      setError('Regeneration failed: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setLoadingRegen(false)
    }
  }

  function handleApprove() {
    if (!job) return
    onApprove({ job, cover_letter: coverLetter, notes, approved_at: new Date().toISOString() })
    setStatus(`Approved: ${job.title} @ ${institution}`)
  }

  function handleDownload() {
    if (!coverLetter) return
    const blob = new Blob([coverLetter], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cover_letter.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">

      {/* Section header */}
      <div className="py-4">
        <p className="text-[10px] font-mono tracking-widest uppercase text-[#818cf8] mb-2">Application review</p>
        <h2 className="text-3xl font-bold text-[#e8e8f0]">Review & edit</h2>
        <p className="text-sm text-[#7a7a8f] mt-1">Load a position to see CV tailoring hints and generate a cover letter.</p>
      </div>

      {/* Position selector */}
      <div className="bg-[#17171c] border border-[#2e2e38] p-4">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className={`block ${SECTION_LABEL} mb-1.5`}>Select position to review</label>
            <select
              value={currentJobIdx}
              onChange={e => setCurrentJobIdx(Number(e.target.value))}
              className={INPUT_CLS}
            >
              <option value={-1}>— choose a position —</option>
              {positionChoices.map(({ label, idx }) => (
                <option key={idx} value={idx}>{label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => currentJobIdx >= 0 && handleLoad(currentJobIdx)}
            disabled={loading || currentJobIdx < 0}
            className="shrink-0 border border-[#818cf8] text-[#818cf8] font-mono text-xs tracking-widest uppercase px-4 py-2 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors disabled:border-[#2e2e38] disabled:text-[#7a7a8f] disabled:cursor-not-allowed"
          >
            {loading ? 'Loading…' : 'Load'}
          </button>
        </div>
        {status && (
          <p className="mt-2 text-xs font-mono text-emerald-500">{status}</p>
        )}
        {error && (
          <p className="mt-2 text-xs font-mono text-red-400">{error}</p>
        )}
      </div>

      {job && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-[#2e2e38]">
            <div className="bg-[#17171c] p-5">
              <p className={`${SECTION_LABEL} mb-3`}>Position details</p>
              <JobDetails job={job} />
            </div>
            <div className="bg-[#17171c] p-5">
              <p className={`${SECTION_LABEL} mb-3`}>CV tailoring hints</p>
              {loading
                ? <p className="text-sm text-[#7a7a8f] animate-pulse">Generating hints…</p>
                : <HintsPanel hints={currentHints} />
              }
            </div>
          </div>

          <div className="bg-[#17171c] border border-[#2e2e38] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <p className={SECTION_LABEL}>Cover letter draft</p>
              <p className="text-[10px] font-mono text-[#7a7a8f]">Edit before sending · remove the DRAFT header</p>
            </div>
            {loading ? (
              <div className="h-48 bg-[#0f0f12] border border-[#2e2e38] animate-pulse" />
            ) : (
              <textarea
                value={coverLetter}
                onChange={e => setCoverLetter(e.target.value)}
                rows={14}
                placeholder="Load a position to generate a cover letter…"
                className={`${INPUT_CLS} font-mono resize-y`}
              />
            )}
            <div>
              <label className={`block ${SECTION_LABEL} mb-1.5`}>Your notes (optional)</label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={2}
                placeholder="Personal notes about this application…"
                className={`${INPUT_CLS} resize-none`}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleApprove}
                disabled={!coverLetter}
                className="border border-[#818cf8] text-[#818cf8] font-mono text-xs tracking-widest uppercase px-4 py-2 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors disabled:border-[#2e2e38] disabled:text-[#7a7a8f] disabled:cursor-not-allowed"
              >
                Approve & Save
              </button>
              <button
                onClick={handleRegen}
                disabled={loadingRegen || !profileText}
                className="border border-[#2e2e38] text-[#7a7a8f] font-mono text-xs tracking-widest uppercase px-4 py-2 hover:border-[#7a7a8f] hover:text-[#e8e8f0] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loadingRegen ? 'Regenerating…' : 'Regenerate Letter'}
              </button>
              <button
                onClick={handleDownload}
                disabled={!coverLetter}
                className="border border-[#2e2e38] text-[#7a7a8f] font-mono text-xs tracking-widest uppercase px-4 py-2 hover:border-[#7a7a8f] hover:text-[#e8e8f0] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Download .txt
              </button>
            </div>
          </div>
        </>
      )}

      {!job && (
        <div className="bg-[#17171c] border border-[#2e2e38] p-12 text-center  text-[#7a7a8f]">
          Select a position above and click Load to start reviewing.
        </div>
      )}
    </div>
  )
}
