import { useState } from 'react'
import SearchTab from './components/SearchTab.jsx'
import ResultsTab from './components/ResultsTab.jsx'
import ReviewTab from './components/ReviewTab.jsx'
import ExportTab from './components/ExportTab.jsx'

const TABS = ['Search', 'Results', 'Review', 'Export']

export default function App() {
  const [tab, setTab] = useState(0)

  // Shared session state (no backend storage — lives in browser)
  const [profile, setProfile] = useState(null)
  const [profileText, setProfileText] = useState('')
  const [scoredJobs, setScoredJobs] = useState([])
  const [approved, setApproved] = useState([])

  // Review state
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
      const job = entry.job
      const alreadyIn = prev.some(
        a => a.job.title === job.title && a.job.institution === job.institution
      )
      return alreadyIn ? prev : [...prev, entry]
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <span className="text-2xl">🎓</span>
          <div>
            <h1 className="text-xl font-bold text-gray-900 leading-tight">PhdScout</h1>
            <p className="text-xs text-gray-500">AI-powered academic job search</p>
          </div>
          <div className="ml-auto text-xs text-gray-400 hidden sm:block">
            Free · No sign-up · Powered by Groq
          </div>
        </div>

        {/* Tab navigation */}
        <div className="max-w-6xl mx-auto px-4">
          <nav className="flex gap-1">
            {TABS.map((name, i) => {
              const disabled = (i === 1 && scoredJobs.length === 0)
                || (i === 2 && scoredJobs.length === 0)
                || (i === 3 && approved.length === 0)
              return (
                <button
                  key={name}
                  onClick={() => !disabled && setTab(i)}
                  className={[
                    'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                    tab === i
                      ? 'border-blue-600 text-blue-600'
                      : disabled
                        ? 'border-transparent text-gray-300 cursor-not-allowed'
                        : 'border-transparent text-gray-500 hover:text-gray-900 hover:border-gray-300',
                  ].join(' ')}
                >
                  {name}
                  {i === 1 && scoredJobs.length > 0 && (
                    <span className="ml-1.5 text-xs bg-blue-100 text-blue-700 rounded-full px-1.5 py-0.5">
                      {scoredJobs.length}
                    </span>
                  )}
                  {i === 3 && approved.length > 0 && (
                    <span className="ml-1.5 text-xs bg-green-100 text-green-700 rounded-full px-1.5 py-0.5">
                      {approved.length}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      {/* Tab content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">
        {tab === 0 && (
          <SearchTab onDone={handleSearchDone} />
        )}
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
            onGoExport={() => setTab(3)}
          />
        )}
        {tab === 3 && (
          <ExportTab approved={approved} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 py-3 text-xs text-gray-400 flex flex-wrap gap-4">
          <span>© 2025 PhdScout</span>
          <span>CVs are processed in memory and never stored</span>
          <span>Sources: Euraxess · ScholarshipDb · Nature Careers · mlscientist.com</span>
        </div>
      </footer>
    </div>
  )
}
