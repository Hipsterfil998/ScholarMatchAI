import { useState } from 'react'
import SearchTab from './components/SearchTab.jsx'
import ResultsTab from './components/ResultsTab.jsx'
import ReviewTab from './components/ReviewTab.jsx'
import ExportTab from './components/ExportTab.jsx'

export default function App() {
  const [tab, setTab] = useState(0)
  const [profile, setProfile] = useState(null)
  const [profileText, setProfileText] = useState('')
  const [scoredJobs, setScoredJobs] = useState([])
  const [approved, setApproved] = useState([])
  const [currentJobIdx, setCurrentJobIdx] = useState(-1)
  const [currentHints, setCurrentHints] = useState(null)
  const [coverLetter, setCoverLetter] = useState('')

  function handleSearchDone({ profile, profileText, scoredJobs }) {
    setProfile(profile)
    setProfileText(profileText)
    setScoredJobs(scoredJobs)
    setCurrentJobIdx(-1)
    setCurrentHints(null)
    setCoverLetter('')
    setTab(1)
  }

  function handleSelectJob(idx) {
    setCurrentJobIdx(idx)
    setCurrentHints(null)
    setCoverLetter('')
    setTab(2)
  }

  function handleApprove(entry) {
    setApproved(prev => {
      const { title, institution } = entry.job
      return prev.some(a => a.job.title === title && a.job.institution === institution)
        ? prev
        : [...prev, entry]
    })
  }

  const TABS = [
    { name: 'Search',  badge: null,                    disabled: false },
    { name: 'Results', badge: scoredJobs.length || null, disabled: scoredJobs.length === 0 },
    { name: 'Review',  badge: null,                    disabled: scoredJobs.length === 0 },
    { name: 'Export',  badge: approved.length || null,  disabled: approved.length === 0 },
  ]

  return (
    <div className="min-h-screen bg-[#0e0e0e] flex flex-col">
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#272320] bg-[#0e0e0e]/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-4">
          <span className="font-mono font-semibold text-sm tracking-wider text-[#e8e2d9] link-underline">
            PhdScout
          </span>
          <div className="ml-auto text-[10px] font-mono tracking-widest uppercase text-[#6b6560] hidden sm:block">
            Free · No sign-up · Powered by Groq
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-4">
          <nav className="flex gap-0">
            {TABS.map(({ name, badge, disabled }, i) => (
              <button
                key={name}
                onClick={() => !disabled && setTab(i)}
                className={[
                  'px-4 py-2.5 text-[10px] font-mono tracking-widest uppercase border-b-2 transition-colors',
                  tab === i
                    ? 'border-[#d97706] text-[#d97706]'
                    : disabled
                      ? 'border-transparent text-[#272320] cursor-not-allowed'
                      : 'border-transparent text-[#6b6560] hover:text-[#e8e2d9]',
                ].join(' ')}
              >
                {name}
                {badge !== null && (
                  <span className="ml-1.5 text-[9px] text-[#d97706] border border-[#d97706]/40 px-1.5 py-0.5">
                    {badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6 pt-20">
        {tab === 0 && <SearchTab onDone={handleSearchDone} />}
        {tab === 1 && (
          <ResultsTab
            profile={profile}
            scoredJobs={scoredJobs}
            onSelectJob={handleSelectJob}
            onGoReview={() => setTab(2)}
          />
        )}
        {tab === 2 && (
          <ReviewTab
            scoredJobs={scoredJobs}
            profileText={profileText}
            currentJobIdx={currentJobIdx}
            setCurrentJobIdx={setCurrentJobIdx}
            currentHints={currentHints}
            setCurrentHints={setCurrentHints}
            coverLetter={coverLetter}
            setCoverLetter={setCoverLetter}
            onApprove={handleApprove}
          />
        )}
        {tab === 3 && <ExportTab approved={approved} />}
      </main>

      <footer className="border-t border-[#272320]">
        <div className="max-w-6xl mx-auto px-4 py-3 text-[10px] font-mono tracking-wide text-[#6b6560] flex flex-wrap gap-4">
          <span>© 2025 PhdScout</span>
          <span>CVs are processed in memory and never stored</span>
          <span>Sources: Euraxess · ScholarshipDb · Nature Careers · mlscientist.com</span>
        </div>
      </footer>
    </div>
  )
}
