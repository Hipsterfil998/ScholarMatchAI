import { useState } from 'react'
import { prepareApplication, regenerateLetter } from '../api.js'
import { REC_CONFIG } from '../constants.js'

function JobDetails({ job }) {
  const match = job.match || {}
  const score = match.match_score || 0
  const filled = Math.round(score / 10)
  const bar = '🟩'.repeat(filled) + '⬜'.repeat(10 - filled)
  const rec = match.recommendation || ''
  const recCfg = REC_CONFIG[rec] || {}
  const institution = job.institution || job.company || ''

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold text-gray-900 text-base leading-tight">{job.title}</h3>
        <p className="text-sm text-gray-500 mt-0.5">
          {institution}{institution && job.location ? ' · ' : ''}{job.location}
        </p>
        {job.url && (
          <a href={job.url} target="_blank" rel="noreferrer"
            className="text-xs text-blue-600 hover:underline break-all">
            {job.url}
          </a>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        {job.type && (
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-gray-400">Type</p>
            <p className="font-medium text-gray-700 capitalize">{job.type}</p>
          </div>
        )}
        {job.deadline && (
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-gray-400">Deadline</p>
            <p className="font-medium text-gray-700">{job.deadline}</p>
          </div>
        )}
        {job.source && (
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-gray-400">Source</p>
            <p className="font-medium text-gray-700">{job.source}</p>
          </div>
        )}
        {job.freshness && (
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-gray-400">Freshness</p>
            <p className="font-medium text-gray-700">{job.freshness}</p>
          </div>
        )}
      </div>

      <div className="border border-gray-100 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-gray-700">Match score</p>
          <span className="text-lg font-bold text-gray-900">{score}/100</span>
        </div>
        <p className="text-lg">{bar}</p>
        {rec && (
          <span className={`inline-flex text-xs px-2.5 py-1 rounded-full border font-medium ${recCfg.color || ''}`}>
            {recCfg.icon} Recommendation: {recCfg.label}
          </span>
        )}
        {match.why_good_fit && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Why a good fit</p>
            <p className="text-sm text-gray-600 mt-0.5">{match.why_good_fit}</p>
          </div>
        )}
        {match.concerns && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Concerns</p>
            <p className="text-sm text-gray-600 mt-0.5">{match.concerns}</p>
          </div>
        )}
        {(match.matching_areas || []).length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Matching areas</p>
            <ul className="mt-0.5 space-y-0.5">
              {match.matching_areas.map((a, i) => (
                <li key={i} className="text-xs text-gray-600">✓ {a}</li>
              ))}
            </ul>
          </div>
        )}
        {(match.missing_requirements || []).length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Missing requirements</p>
            <ul className="mt-0.5 space-y-0.5">
              {match.missing_requirements.map((r, i) => (
                <li key={i} className="text-xs text-gray-600">⚠ {r}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {job.description && (
        <details className="text-xs">
          <summary className="cursor-pointer text-gray-500 hover:text-gray-700 font-medium">
            📄 Full description
          </summary>
          <p className="mt-2 text-gray-600 whitespace-pre-wrap leading-relaxed">{job.description}</p>
        </details>
      )}
    </div>
  )
}

function HintsPanel({ hints }) {
  if (!hints) return (
    <p className="text-sm text-gray-400 italic">Load a position to see CV tailoring hints.</p>
  )

  return (
    <div className="space-y-4">
      {hints.headline_suggestion && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Profile summary tweak</p>
          <blockquote className="border-l-2 border-blue-400 pl-3 text-sm text-gray-600 italic">
            {hints.headline_suggestion}
          </blockquote>
        </div>
      )}
      {hints.research_alignment && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Research alignment</p>
          <blockquote className="border-l-2 border-blue-400 pl-3 text-sm text-gray-600 italic">
            {hints.research_alignment}
          </blockquote>
        </div>
      )}
      {(hints.skills_to_highlight || []).length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Skills to highlight</p>
          <ul className="space-y-1">
            {hints.skills_to_highlight.map((s, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm text-gray-600">
                <input type="checkbox" className="mt-0.5 accent-blue-600" readOnly />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(hints.experience_to_emphasize || []).length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Experience to highlight</p>
          <ul className="space-y-1">
            {hints.experience_to_emphasize.map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm text-gray-600">
                <input type="checkbox" className="mt-0.5 accent-blue-600" readOnly />
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(hints.keywords_to_add || []).length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Keywords to add</p>
          <div className="flex flex-wrap gap-1">
            {hints.keywords_to_add.map((k, i) => (
              <code key={i} className="text-xs bg-gray-100 text-gray-700 rounded px-1.5 py-0.5">{k}</code>
            ))}
          </div>
        </div>
      )}
      {(hints.suggested_order || []).length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Suggested section order</p>
          <ol className="space-y-0.5 list-decimal list-inside">
            {hints.suggested_order.map((s, i) => (
              <li key={i} className="text-sm text-gray-600">{s}</li>
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
  onGoExport,
}) {
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingRegen, setLoadingRegen] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const job = currentJobIdx >= 0 ? scoredJobs[currentJobIdx] : null
  const institution = job ? (job.institution || job.company || '') : ''

  const positionChoices = scoredJobs.map((j, i) => {
    const score = j.match?.match_score || 0
    const inst = j.institution || j.company || 'Unknown'
    return { label: `[${score}] ${inst} — ${j.title || 'Unknown'}`, idx: i }
  })

  async function handleLoad(idx) {
    setCurrentJobIdx(idx)
    setCurrentHints(null)
    setCoverLetter('')
    setStatus('')
    setError('')
    setLoading(true)

    try {
      const { hints, cover_letter } = await prepareApplication({
        job: scoredJobs[idx],
        profileText,
      })
      setCurrentHints(hints)
      setCoverLetter(cover_letter)
      setStatus(`✅ Loaded: ${scoredJobs[idx].title} @ ${scoredJobs[idx].institution || 'Unknown'}`)
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
    onApprove({
      job,
      cover_letter: coverLetter,
      notes,
      approved_at: new Date().toISOString(),
    })
    setStatus(`✅ Approved: ${job.title} @ ${institution}`)
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
    <div className="space-y-5">
      {/* Position selector */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select position to review
            </label>
            <select
              value={currentJobIdx}
              onChange={e => setCurrentJobIdx(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="shrink-0 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
              hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Loading…' : 'Load'}
          </button>
        </div>

        {status && (
          <p className="mt-2 text-sm text-green-700">{status}</p>
        )}
        {error && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}
      </div>

      {/* Details + Hints */}
      {job && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Position details
              </p>
              <JobDetails job={job} />
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                CV tailoring hints
              </p>
              {loading ? (
                <p className="text-sm text-gray-400 animate-pulse">Generating hints…</p>
              ) : (
                <HintsPanel hints={currentHints} />
              )}
            </div>
          </div>

          {/* Cover letter */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Cover letter draft
              </p>
              <p className="text-xs text-gray-400">Edit before sending · remove the DRAFT header</p>
            </div>
            {loading ? (
              <div className="h-48 bg-gray-50 rounded-lg animate-pulse" />
            ) : (
              <textarea
                value={coverLetter}
                onChange={e => setCoverLetter(e.target.value)}
                rows={14}
                placeholder="Load a position to generate a cover letter…"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono
                  focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              />
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Your notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={2}
                placeholder="Personal notes about this application…"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                  focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleApprove}
                disabled={!coverLetter}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg
                  hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                ✅ Approve & Save
              </button>
              <button
                onClick={handleRegen}
                disabled={loadingRegen || !profileText}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium
                  rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loadingRegen ? 'Regenerating…' : '🔄 Regenerate Letter'}
              </button>
              <button
                onClick={handleDownload}
                disabled={!coverLetter}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium
                  rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                ⬇ Download .txt
              </button>
            </div>
          </div>
        </>
      )}

      {!job && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
          Select a position above and click Load to start reviewing.
        </div>
      )}
    </div>
  )
}
