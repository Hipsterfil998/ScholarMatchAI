import { useState } from 'react'
import { exportZip } from '../api.js'

export default function ExportTab({ approved }) {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  async function handleExport() {
    if (approved.length === 0) return
    setLoading(true)
    setStatus('')
    setError('')
    try {
      const blob = await exportZip(approved)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'phdscout_applications.zip'
      a.click()
      URL.revokeObjectURL(url)
      setStatus(`Downloaded ZIP with ${approved.length} application(s).`)
    } catch (err) {
      setError('Export failed: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  if (approved.length === 0) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-[#17171c] border border-[#2e2e38] rounded p-12 text-center  text-[#7a7a8f]">
          <p className="font-mono text-sm mb-2">No applications approved yet.</p>
          <p className="text-sm mt-1">Go to the Review tab to approve positions.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-xl font-semibold text-[#e8e8f0]">Approved applications ({approved.length})</h2>
        <button
          onClick={handleExport}
          disabled={loading}
          className="border border-[#818cf8] text-[#818cf8] font-mono text-xs tracking-widest uppercase px-5 py-2.5 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors disabled:border-[#2e2e38] disabled:text-[#7a7a8f] disabled:cursor-not-allowed"
        >
          {loading ? 'Generating ZIP…' : 'Download all as ZIP'}
        </button>
      </div>

      {status && (
        <div className="border border-emerald-800 p-3 text-sm font-mono text-emerald-500">
          {status}
        </div>
      )}
      {error && (
        <div className="border border-red-900 p-3 text-sm font-mono text-red-400">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {approved.map((entry, i) => {
          const job = entry.job || {}
          const match = job.match || {}
          const institution = job.institution || job.company || 'Unknown'
          const ts = entry.approved_at ? new Date(entry.approved_at).toLocaleString() : ''
          const score = match.match_score
          const scoreCls = score >= 75
            ? 'border border-emerald-800 text-emerald-500'
            : score >= 55
              ? 'border border-amber-800 text-amber-500'
              : 'border border-red-900 text-red-500'

          return (
            <div key={i} className="bg-[#17171c] border border-[#2e2e38] rounded p-4 hover:border-[#818cf8]/40 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono font-bold text-[#7a7a8f]">#{i + 1}</span>
                    {score !== undefined && (
                      <span className={`text-xs font-mono font-bold px-2 py-0.5 ${scoreCls}`}>
                        {score}
                      </span>
                    )}
                    {job.type && <span className="text-[10px] font-mono text-[#7a7a8f] capitalize">{job.type}</span>}
                  </div>
                  <h4 className="mt-1 font-mono font-semibold text-[#e8e8f0] text-sm">{job.title || 'Unknown'}</h4>
                  <p className="text-xs  text-[#7a7a8f]">
                    {institution}{job.location ? ` · ${job.location}` : ''}
                  </p>
                  {ts && <p className="text-[10px] font-mono text-[#7a7a8f] mt-1">Approved {ts}</p>}
                  {entry.notes && <p className="text-xs  text-[#7a7a8f] mt-1 italic">Note: {entry.notes}</p>}
                </div>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer"
                    className="shrink-0 text-[10px] font-mono text-[#818cf8] link-underline">
                    View →
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="text-[10px] font-mono text-[#7a7a8f] text-center pb-4">
        The ZIP contains a cover letter, notes, and position details JSON for each application.
      </div>
    </div>
  )
}
