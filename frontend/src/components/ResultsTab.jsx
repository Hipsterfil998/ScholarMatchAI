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
    <div className="bg-[#17171c] border border-[#2e2e38] rounded-lg p-5 space-y-3">
      <div>
        <h3 className="font-mono font-semibold text-[#e8e8f0] text-base">{profile.name || 'Unknown'}</h3>
        {contact.email && <p className="text-xs font-mono text-[#7a7a8f]">{contact.email}</p>}
        {contact.linkedin && (
          <a href={contact.linkedin} target="_blank" rel="noreferrer"
            className="text-xs font-mono text-[#818cf8] link-underline">LinkedIn</a>
        )}
      </div>
      {profile.summary && (
        <p className="text-sm  text-[#7a7a8f] leading-relaxed">{profile.summary}</p>
      )}
      {interests.length > 0 && (
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1">Research interests</p>
          <div className="flex flex-wrap gap-1">
            {interests.map((item, idx) => (
              <span key={idx} className="text-xs border border-[#2e2e38] text-[#7a7a8f] px-2 py-0.5">
                {item}
              </span>
            ))}
          </div>
        </div>
      )}
      {education.length > 0 && (
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1">Education</p>
          {education.slice(0, 2).map((e, idx) => (
            <p key={idx} className="text-xs  text-[#7a7a8f]">
              {e.degree} in {e.field} — {e.institution} ({e.year})
            </p>
          ))}
        </div>
      )}
      {allSkills.length > 0 && (
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-1">Skills</p>
          <p className="text-xs  text-[#7a7a8f]">{allSkills.join(', ')}</p>
        </div>
      )}
    </div>
  )
}

function ScoreBadge({ score }) {
  const filled = Math.round(score / 10)
  return (
    <span className="text-sm leading-none" title={`${score}/100`}>
      {'🎓'.repeat(filled)}{'◽'.repeat(10 - filled)}
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
    <div className="bg-[#17171c] border border-[#2e2e38] rounded-lg p-4 hover:border-[#818cf8]/40 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <ScoreBadge score={score} />
            {rec && (
              <span className={`text-xs px-2 py-0.5 border font-mono ${recCfg.color || ''}`}>
                {recCfg.icon} {recCfg.label}
              </span>
            )}
            {job.freshness && <span className="text-[10px] font-mono text-[#7a7a8f]">{job.freshness}</span>}
          </div>
          <h4 className="mt-1.5 font-mono font-semibold text-[#e8e8f0] text-sm leading-snug">
            <a href={job.url} target="_blank" rel="noreferrer" className="hover:text-[#818cf8] link-underline">
              {job.title}
            </a>
          </h4>
          <p className="text-xs font-mono text-[#7a7a8f] mt-0.5">
            {institution}
            {institution && job.location ? ' · ' : ''}
            {job.location}
            {job.type ? ` · ${job.type}` : ''}
          </p>
          {match.why_good_fit && (
            <p className="mt-1.5 text-xs  text-[#7a7a8f] line-clamp-2">
              <span className="font-semibold text-[#e8e8f0]/60">Why: </span>
              {match.why_good_fit}
            </p>
          )}
          {job.deadline && <p className="mt-1 text-[10px] font-mono text-[#7a7a8f]">Deadline: {job.deadline}</p>}
        </div>
        <button
          onClick={() => onSelect(idx)}
          className="shrink-0 border border-[#818cf8] text-[#818cf8] text-[10px] font-mono tracking-widest uppercase px-3 py-1.5 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors"
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
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h2 className="font-mono text-xl font-semibold text-[#e8e8f0]">{scoredJobs.length} positions found</h2>
          <p className="text-sm  text-[#7a7a8f]">{applying} to apply · {considering} to consider</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] whitespace-nowrap">
            Min score: <span className="font-bold text-[#818cf8]">{minScore}</span>
          </label>
          <input
            type="range" min={0} max={90} step={5}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-28 accent-[#818cf8]"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <p className="text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f] mb-2">Your profile</p>
          <ProfileCard profile={profile} />
        </div>
        <div className="lg:col-span-2 space-y-3">
          <p className="text-[10px] font-mono tracking-widest uppercase text-[#7a7a8f]">
            Positions ({filtered.length})
          </p>
          {filtered.length === 0 ? (
            <div className="bg-[#17171c] border border-[#2e2e38] rounded-lg p-8 text-center  text-[#7a7a8f]">
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
