import { useState, useEffect } from 'react'

const STEPS = [
  {
    num: '01',
    title: 'Upload your CV',
    desc: 'Drop your PDF, DOCX, or TXT. The AI extracts your profile: education, publications, skills, and research interests.',
  },
  {
    num: '02',
    title: 'Search 5 job boards',
    desc: 'Set your field, location, and position type. All sources are queried in parallel and results are deduplicated automatically.',
  },
  {
    num: '03',
    title: 'Review, edit & apply',
    desc: 'Every position gets an AI match score (0–100) and a tailored cover letter draft. Edit freely, approve, and export as a ZIP.',
  },
]

const SOURCES = [
  { icon: '🇪🇺', name: 'Euraxess',       desc: 'EU & worldwide research portal' },
  { icon: '🌍', name: 'ScholarshipDB',   desc: '28k+ positions worldwide' },
  { icon: '🔬', name: 'Nature Careers',  desc: 'Multidisciplinary global board' },
  { icon: '🤖', name: 'mlscientist.com', desc: 'ML & AI academic positions' },
  { icon: '🇬🇧', name: 'jobs.ac.uk',     desc: 'UK academic jobs' },
]

const FAQS = [
  {
    q: 'Is ScholarMatchAI really free?',
    a: 'Yes, 100% free. It runs on the Groq free API tier — no subscription, no credit card, no sign-up required. The only requirement to self-host it is a free Groq API key.',
  },
  {
    q: 'Is my CV stored on your servers?',
    a: 'No. Your CV is processed entirely in memory for the duration of the search and is never written to disk or stored in any database.',
  },
  {
    q: 'Which job boards are searched?',
    a: 'Euraxess (EU/worldwide), ScholarshipDB (28k+ positions), Nature Careers (multidisciplinary global), mlscientist.com (ML & AI), and jobs.ac.uk (UK). All five are queried in parallel.',
  },
  {
    q: 'How long does a search take?',
    a: 'CV parsing takes ~10 seconds. The job board search runs in parallel and takes 60–90 seconds. AI scoring depends on the number of results, typically another 30–60 seconds.',
  },
  {
    q: 'How accurate is the AI match score?',
    a: 'The score is a semantic estimate by a large language model — not a keyword counter. "NLP" and "natural language processing" are treated as equivalent. Use it as a guide to prioritise, not as a definitive ranking.',
  },
  {
    q: 'What CV formats are supported?',
    a: 'PDF, DOCX, and plain TXT. For best results, use a well-structured PDF with clear section headings (Education, Publications, Skills, etc.).',
  },
  {
    q: 'What position types are available?',
    a: 'PhD positions, postdocs, predoctoral, fellowships, and research staff. Each type triggers different search queries and scoring criteria.',
  },
]

const STATS = [
  { val: '5',      label: 'Job boards' },
  { val: '40+',    label: 'Countries' },
  { val: '0–100',  label: 'AI match score' },
  { val: '< 3 min', label: 'Per search' },
]

export default function LandingPage({ onStart }) {
  const [openFaq, setOpenFaq] = useState(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible') }),
      { threshold: 0.12 }
    )
    document.querySelectorAll('.reveal').forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  return (
    <div className="min-h-screen bg-[#0f0f12] text-[#e8e8f0]">

      {/* ── Navbar ─────────────────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#2e2e38] bg-[#0f0f12]/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <img src="/logo.svg" alt="ScholarMatchAI" className="w-8 h-8 rounded-lg" />
            <span className="font-mono font-semibold text-sm text-[#e8e8f0]">ScholarMatchAI</span>
          </button>
          <div className="flex items-center gap-4">
            {/* Free badge */}
            <span className="hidden sm:inline-flex items-center gap-1.5 border border-[#2e2e38] bg-[#17171c] px-2.5 py-1 text-[10px] font-mono text-[#7a7a8f]">
              <span className="w-1 h-1 bg-emerald-400 rounded-full" />
              100% free · No sign-up · Powered by{' '}
              <a href="https://groq.com" target="_blank" rel="noreferrer" className="text-[#818cf8] hover:text-[#a5b4fc] transition-colors">Groq</a>
            </span>
            {/* Docs icon */}
            <a
              href="https://hipsterfil998.github.io/ScholarMatchAI"
              target="_blank" rel="noreferrer"
              title="Documentation"
              className="text-[#7a7a8f] hover:text-[#e8e8f0] transition-colors hidden sm:block"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
            </a>
            {/* GitHub icon */}
            <a
              href="https://github.com/Hipsterfil998/ScholarMatchAI"
              target="_blank" rel="noreferrer"
              title="GitHub"
              className="text-[#7a7a8f] hover:text-[#e8e8f0] transition-colors hidden sm:block"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
              </svg>
            </a>
            <button
              onClick={onStart}
              className="border border-[#818cf8] text-[#818cf8] font-mono text-xs tracking-widest uppercase px-4 py-2 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors"
            >
              Open App →
            </button>
          </div>
        </div>
      </header>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="relative pt-36 pb-28 px-6 overflow-hidden dot-grid">
        {/* ambient glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[700px] h-[500px] bg-[#818cf8]/[0.07] rounded-full blur-3xl animate-glow" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center">
          {/* heading */}
          <h1
            className="animate-fade-in-up text-4xl sm:text-6xl font-bold tracking-tight leading-[1.1] mb-6"
            style={{ animationDelay: '0.1s' }}
          >
            Find your next<br />
            <span className="gradient-text">academic position</span>,<br />
            prepare your application<br />
            with AI
          </h1>

          {/* subtitle */}
          <p
            className="animate-fade-in-up text-lg text-[#7a7a8f] max-w-2xl mx-auto mb-4 leading-relaxed"
            style={{ animationDelay: '0.22s' }}
          >
            Upload your CV, set your research field and location. ScholarMatchAI searches 5 job boards,
            scores every position against your profile, and drafts a tailored cover letter. All in under 3 minutes.
          </p>
          <p
            className="animate-fade-in-up text-sm text-[#7a7a8f] max-w-xl mx-auto mb-10 leading-relaxed border-l-2 border-[#818cf8]/50 bg-[#17171c] px-4 py-3 text-left"
            style={{ animationDelay: '0.28s' }}
          >
            ScholarMatchAI is a human-in-the-loop tool. The AI handles the tedious parts like searching, scoring, and drafting, but{' '}
            <span className="text-[#e8e8f0] font-medium">every decision is yours</span>.
            {' '}Read, edit, and approve each application before sending it.
          </p>

          {/* CTAs */}
          <div
            className="animate-fade-in-up flex flex-wrap gap-3 justify-center mb-16"
            style={{ animationDelay: '0.34s' }}
          >
            <button
              onClick={onStart}
              className="bg-[#818cf8] text-[#0f0f12] font-mono text-sm font-semibold tracking-widest uppercase px-8 py-3 hover:bg-[#a5b4fc] transition-colors"
            >
              Start searching →
            </button>
            <a
              href="https://hipsterfil998.github.io/ScholarMatchAI"
              target="_blank" rel="noreferrer"
              className="border border-[#2e2e38] text-[#7a7a8f] font-mono text-sm tracking-widest uppercase px-8 py-3 hover:border-[#7a7a8f] hover:text-[#e8e8f0] transition-colors"
            >
              Documentation
            </a>
          </div>

          {/* stats */}
          <div
            className="animate-fade-in-up grid grid-cols-2 sm:grid-cols-4 gap-px border border-[#2e2e38] bg-[#2e2e38]"
            style={{ animationDelay: '0.46s' }}
          >
            {STATS.map(({ val, label }) => (
              <div key={label} className="bg-[#17171c] py-5 px-4 text-center">
                <p className="font-mono font-bold text-2xl text-[#818cf8]">{val}</p>
                <p className="text-[11px] font-mono text-[#7a7a8f] mt-1 tracking-wide">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────── */}
      <section className="py-24 px-6 border-t border-[#2e2e38]">
        <div className="max-w-5xl mx-auto">
          <div className="reveal text-center mb-14">
            <p className="text-[10px] font-mono tracking-widest uppercase text-[#818cf8] mb-3">How it works</p>
            <h2 className="text-3xl font-bold">From CV to application in minutes</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[#2e2e38]">
            {STEPS.map((step, i) => (
              <div
                key={i}
                className="reveal bg-[#17171c] p-8 hover:bg-[#1c1c23] transition-colors"
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                <p className="font-mono text-4xl font-bold text-[#818cf8]/25 mb-5 leading-none">{step.num}</p>
                <h3 className="font-mono font-semibold text-[#e8e8f0] mb-3">{step.title}</h3>
                <p className="text-sm text-[#7a7a8f] leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Sources ────────────────────────────────────────────── */}
      <section className="py-24 px-6 border-t border-[#2e2e38]">
        <div className="max-w-5xl mx-auto">
          <div className="reveal text-center mb-14">
            <p className="text-[10px] font-mono tracking-widest uppercase text-[#818cf8] mb-3">Data sources</p>
            <h2 className="text-3xl font-bold">Searches 5 job boards simultaneously</h2>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            {SOURCES.map((s, i) => (
              <div
                key={i}
                className="reveal flex items-center gap-3 bg-[#17171c] border border-[#2e2e38] px-5 py-4 hover:border-[#818cf8]/40 transition-colors"
                style={{ transitionDelay: `${i * 60}ms` }}
              >
                <span className="text-2xl">{s.icon}</span>
                <div>
                  <p className="font-mono text-sm font-medium text-[#e8e8f0]">{s.name}</p>
                  <p className="text-xs text-[#7a7a8f] mt-0.5">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ────────────────────────────────────────────────── */}
      <section className="py-24 px-6 border-t border-[#2e2e38]">
        <div className="max-w-3xl mx-auto">
          <div className="reveal text-center mb-14">
            <p className="text-[10px] font-mono tracking-widest uppercase text-[#818cf8] mb-3">FAQ</p>
            <h2 className="text-3xl font-bold">Common questions</h2>
          </div>
          <div className="space-y-px bg-[#2e2e38]">
            {FAQS.map((faq, i) => {
              const open = openFaq === i
              return (
                <div key={i} className="reveal bg-[#17171c]" style={{ transitionDelay: `${i * 40}ms` }}>
                  <button
                    onClick={() => setOpenFaq(open ? null : i)}
                    className="w-full flex items-center justify-between px-6 py-5 text-left gap-4 hover:bg-[#1c1c23] transition-colors"
                  >
                    <span className="font-mono text-sm font-medium text-[#e8e8f0]">{faq.q}</span>
                    <span
                      className="shrink-0 font-mono text-[#818cf8] text-xl leading-none transition-transform duration-200"
                      style={{ transform: open ? 'rotate(45deg)' : 'rotate(0deg)' }}
                    >
                      +
                    </span>
                  </button>
                  <div
                    className="overflow-hidden transition-all duration-300 ease-in-out"
                    style={{ maxHeight: open ? '200px' : '0px' }}
                  >
                    <p className="px-6 pb-5 text-sm text-[#7a7a8f] leading-relaxed">{faq.a}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── Report issue ───────────────────────────────────────── */}
      <section className="py-24 px-6 border-t border-[#2e2e38]">
        <div className="max-w-2xl mx-auto text-center reveal">
          <p className="text-[10px] font-mono tracking-widest uppercase text-[#818cf8] mb-3">Support</p>
          <h2 className="text-3xl font-bold mb-4">Found a bug?</h2>
          <p className="text-[#7a7a8f] mb-8 leading-relaxed max-w-lg mx-auto">
            ScholarMatchAI is open source under AGPL-3.0. If you encounter an issue or have a feature request,
            open a ticket on GitHub — it takes 30 seconds.
          </p>
          <a
            href="https://github.com/Hipsterfil998/ScholarMatchAI/issues/new"
            target="_blank" rel="noreferrer"
            className="inline-block border border-[#818cf8] text-[#818cf8] font-mono text-xs tracking-widest uppercase px-8 py-3 hover:bg-[#818cf8] hover:text-[#0f0f12] transition-colors"
          >
            Open an issue →
          </a>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="border-t border-[#2e2e38] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="flex items-center gap-3 hover:opacity-70 transition-opacity">
            <img src="/logo.svg" alt="" className="w-5 h-5 rounded" />
            <span className="text-[10px] font-mono text-[#7a7a8f]">© 2026 ScholarMatchAI</span>
          </button>
          <div className="flex gap-6 text-[10px] font-mono text-[#7a7a8f]">
            <a href="https://github.com/Hipsterfil998/ScholarMatchAI" target="_blank" rel="noreferrer" className="hover:text-[#e8e8f0] transition-colors">GitHub</a>
            <a href="https://hipsterfil998.github.io/ScholarMatchAI" target="_blank" rel="noreferrer" className="hover:text-[#e8e8f0] transition-colors">Docs</a>
            <a href="https://github.com/Hipsterfil998/ScholarMatchAI/issues" target="_blank" rel="noreferrer" className="hover:text-[#e8e8f0] transition-colors">Issues</a>
            <span>AGPL-3.0</span>
          </div>
        </div>
      </footer>

    </div>
  )
}
