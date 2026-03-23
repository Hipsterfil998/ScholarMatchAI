import { useState } from 'react'
import { REC_CONFIG } from '../constants.js'

function ProfileCard({ profile }) {
  if (!profile) return null
  const contact = profile.contact || {}
  const interests = profile.research_interests || []
  const education = profile.education || []
  const skills = profile.skills || {}
  const allSkills = [...(skills.programming || []), ...(skills.tools || [])].slice(0, 12)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
      <div>
        <h3 className="font-bold text-gray-900 text-lg">{profile.name || 'Unknown'}</h3>
        {contact.email && <p className="text-xs text-gray-500">{contact.email}</p>}
        {contact.linkedin && (
          <a href={contact.linkedin} target="_blank" rel="noreferrer"
            className="text-xs text-blue-600 hover:underline">LinkedIn</a>
        )}
      </div>
      {profile.summary && (
        <p className="text-sm text-gray-600 leading-relaxed">{profile.summary}</p>
      )}
      {interests.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Research interests</p>
          <div className="flex flex-wrap gap-1">
            {interests.map((i, idx) => (
              <span key={idx} className="text-xs bg-blue-50 text-blue-700 rounded-full px-2 py-0.5">{i}</span>
            ))}
          </div>
        </div>
      )}
      {education.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Education</p>
          {education.slice(0, 2).map((e, idx) => (
            <p key={idx} className="text-xs text-gray-600">
              {e.degree} in {e.field} — {e.institution} ({e.year})
            </p>
          ))}
        </div>
      )}
      {allSkills.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Skills</p>
          <p className="text-xs text-gray-600">{allSkills.join(', ')}</p>
        </div>
      )}
    </div>
  )
}

function ScoreBadge({ score }) {
  const color = score >= 75
    ? 'bg-green-100 text-green-800'
    : score >= 55
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${color}`}>
      {score}
    </span>
  )
}

function JobCard({ job, idx, onSelect }) {
  const match = job.match || {}
  const score = match.match_score || 0
  const rec = match.recommendation || ''
  const recCfg = REC_CONFIG[rec] || {}
  const institution = job.institution || job.company || ''

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <ScoreBadge score={score} />
            {rec && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${recCfg.color || ''}`}>
                {recCfg.icon} {recCfg.label}
              </span>
            )}
            {job.freshness && (
              <span className="text-xs text-gray-400">{job.freshness}</span>
            )}
          </div>
          <h4 className="mt-1.5 font-semibold text-gray-900 text-sm leading-snug">
            <a href={job.url} target="_blank" rel="noreferrer"
              className="hover:text-blue-600 hover:underline">
              {job.title}
            </a>
          </h4>
          <p className="text-xs text-gray-500 mt-0.5">
            {institution && <span>{institution}</span>}
            {institution && job.location && <span> · </span>}
            {job.location && <span>{job.location}</span>}
            {job.type && <span> · {job.type}</span>}
          </p>
          {match.why_good_fit && (
            <p className="mt-1.5 text-xs text-gray-600 line-clamp-2">
              <span className="font-medium text-gray-700">Why: </span>
              {match.why_good_fit}
            </p>
          )}
          {job.deadline && (
            <p className="mt-1 text-xs text-gray-400">Deadline: {job.deadline}</p>
          )}
        </div>
        <button
          onClick={() => onSelect(idx)}
          className="shrink-0 text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Review →
        </button>
      </div>
    </div>
  )
}

export default function ResultsTab({ profile, scoredJobs, onSelectJob }) {
  const [minScore, setMinScore] = useState(0)

  const filtered = scoredJobs.filter(j => (j.match?.match_score || 0) >= minScore)
  const applying = filtered.filter(j => j.match?.recommendation === 'apply').length
  const considering = filtered.filter(j => j.match?.recommendation === 'consider').length

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h2 className="text-xl font-bold text-gray-900">
            {scoredJobs.length} positions found
          </h2>
          <p className="text-sm text-gray-500">
            ✅ {applying} to apply · 🟡 {considering} to consider
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 whitespace-nowrap">
            Min score: <span className="font-bold text-blue-600">{minScore}</span>
          </label>
          <input
            type="range" min={0} max={90} step={5}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-28 accent-blue-600"
          />
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile sidebar */}
        <div className="lg:col-span-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Your profile</p>
          <ProfileCard profile={profile} />
        </div>

        {/* Job list */}
        <div className="lg:col-span-2 space-y-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Positions ({filtered.length})
          </p>
          {filtered.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              No positions above score {minScore}. Lower the filter to see more.
            </div>
          ) : (
            filtered.map((job, idx) => (
              <JobCard
                key={job.url || idx}
                job={job}
                idx={scoredJobs.indexOf(job)}
                onSelect={onSelectJob}
              />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
