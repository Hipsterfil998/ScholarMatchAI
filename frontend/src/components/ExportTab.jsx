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
      setStatus(`✅ Downloaded ZIP with ${approved.length} application(s).`)
    } catch (err) {
      setError('Export failed: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  if (approved.length === 0) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
          <p className="text-2xl mb-2">📭</p>
          <p>No applications approved yet.</p>
          <p className="text-sm mt-1">Go to the Review tab to approve positions.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">
          Approved applications ({approved.length})
        </h2>
        <button
          onClick={handleExport}
          disabled={loading}
          className="px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl
            hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {loading ? 'Generating ZIP…' : '⬇ Download all as ZIP'}
        </button>
      </div>

      {status && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700">
          {status}
        </div>
      )}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Approved list */}
      <div className="space-y-3">
        {approved.map((entry, i) => {
          const job = entry.job || {}
          const match = job.match || {}
          const institution = job.institution || job.company || 'Unknown'
          const ts = entry.approved_at
            ? new Date(entry.approved_at).toLocaleString()
            : ''

          return (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-gray-400">#{i + 1}</span>
                    {match.match_score !== undefined && (
                      <span className="text-xs bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 font-bold">
                        {match.match_score}
                      </span>
                    )}
                    {job.type && (
                      <span className="text-xs text-gray-400 capitalize">{job.type}</span>
                    )}
                  </div>
                  <h4 className="mt-1 font-semibold text-gray-900 text-sm">{job.title || 'Unknown'}</h4>
                  <p className="text-xs text-gray-500">
                    {institution}
                    {job.location ? ` · ${job.location}` : ''}
                  </p>
                  {ts && (
                    <p className="text-xs text-gray-400 mt-1">Approved {ts}</p>
                  )}
                  {entry.notes && (
                    <p className="text-xs text-gray-600 mt-1 italic">Note: {entry.notes}</p>
                  )}
                </div>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-xs text-blue-600 hover:underline"
                  >
                    View →
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="text-xs text-gray-400 text-center pb-4">
        The ZIP contains a cover letter, notes, and position details JSON for each application.
      </div>
    </div>
  )
}
