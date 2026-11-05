import { useState } from 'react'
import './App.css'

// Backend address comes from frontend/.env (VITE_API_URL), not hardcoded
const API_URL = import.meta.env.VITE_API_URL

// Status text -> CSS class (for the colour)
const STATUS_CLASS = {
  'Verified': 'verified',
  'Partial': 'partial',
  'No evidence': 'none',
}

function App() {
  // Form inputs
  const [file, setFile] = useState(null)
  const [username, setUsername] = useState('')
  const [skills, setSkills] = useState('')
  // "recruiter" = interview questions, "self" = fix-it list for the candidate
  const [view, setView] = useState('recruiter')

  // What the page is showing
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault() // stop the browser from reloading the page

    if (!API_URL) {
      setError('VITE_API_URL is not set. Add it to frontend/.env and restart npm run dev.')
      return
    }
    if (!file) {
      setError('Please choose a resume file (PDF or DOCX).')
      return
    }

    // Multipart form data, the same as an HTML file-upload form
    const formData = new FormData()
    formData.append('resume', file)
    formData.append('github_username', username)
    formData.append('required_skills', skills)
    formData.append('view', view)

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/api/check`, {
        method: 'POST',
        body: formData,
      })
      // If the reply isn't JSON, use an empty object so we still show an error
      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        // FastAPI puts our error message in "detail"
        setError(data.detail || `Something went wrong (error ${response.status}).`)
      } else {
        setResult(data)
      }
    } catch {
      setError('Could not reach the ProofCheck server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <header className="header">
        <h1>ProofCheck</h1>
        <p className="caption">
          Checks resume claims against GitHub evidence and suggests interview
          questions. It never rejects a candidate.
        </p>
      </header>

      <div className="view-switch">
        <button
          type="button"
          className={view === 'recruiter' ? 'active' : ''}
          onClick={() => setView('recruiter')}
        >
          Recruiter
        </button>
        <button
          type="button"
          className={view === 'self' ? 'active' : ''}
          onClick={() => setView('self')}
        >
          Check myself
        </button>
      </div>

      <form className="card form" onSubmit={handleSubmit}>
        <label>
          Resume (PDF or DOCX)
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setFile(e.target.files[0] || null)}
          />
        </label>

        <label>
          {view === 'self' ? 'Your GitHub username' : 'GitHub username'}
          <input
            type="text"
            placeholder="e.g. octocat"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </label>

        <label>
          Required skills (comma separated)
          <input
            type="text"
            placeholder="e.g. Python, React, SQL"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
          />
        </label>

        <button type="submit" disabled={loading}>
          {loading ? 'Checking…' : 'Check'}
        </button>

        {loading && (
          <p className="hint">Reading the resume and checking GitHub. This can take up to a minute.</p>
        )}
      </form>

      {error && <div className="error">{error}</div>}

      {result && <Report result={result} />}
    </main>
  )
}

// The results section, shown after a successful check
function Report({ result }) {
  const fit = result.job_fit

  return (
    <section className="report">
      <span className={`badge ${result.mode}`}>
        {result.mode === 'ai' ? 'AI mode' : 'Basic mode (no AI)'}
      </span>

      <div className="card fit">
        <div className="fit-score">{fit.score}%</div>
        <div>
          <h2>Job fit</h2>
          <p className="muted">Required skills found in the resume</p>
          <div className="chips">
            {fit.matched.map((s) => <span key={s} className="chip yes">{s}</span>)}
            {fit.missing.map((s) => <span key={s} className="chip no">{s}</span>)}
          </div>
        </div>
      </div>

      <h2 className="section-title">Projects</h2>
      {result.projects.length === 0 && <p className="muted">No projects found in the resume.</p>}
      {result.projects.map((p) => <ProjectCard key={p.project} project={p} />)}

      {result.view === 'self' ? (
        <>
          <h2 className="section-title">Fix-it list</h2>
          <ol className="card questions">
            {result.fixes.map((tip) => <li key={tip}>{tip}</li>)}
          </ol>
        </>
      ) : (
        <>
          <h2 className="section-title">Interview questions</h2>
          <ol className="card questions">
            {result.questions.map((q) => <li key={q}>{q}</li>)}
          </ol>
        </>
      )}
    </section>
  )
}

// One card per resume project
function ProjectCard({ project }) {
  const techList = Object.entries(project.tech) // [["React", true], ["Redis", false]]

  return (
    <article className={`card project ${STATUS_CLASS[project.status]}`}>
      <div className="project-head">
        <h3>{project.project}</h3>
        <span className={`status ${STATUS_CLASS[project.status]}`}>{project.status}</span>
      </div>

      <p className="muted">
        GitHub repo: {project.repo ? <strong>{project.repo}</strong> : 'no matching repo found'}
      </p>

      {techList.length > 0 && (
        <ul className="tech">
          {techList.map(([tech, found]) => (
            <li key={tech} className={found ? 'yes' : 'no'}>
              {found ? '✓' : '✗'} {tech}
            </li>
          ))}
        </ul>
      )}

      {project.repo && (
        <div className="timeline">
          {project.timeline.length > 0 && <CommitChart weeks={project.timeline} />}
          <p className="muted">{project.timeline_label}</p>
        </div>
      )}

      {project.flags.map((flag) => (
        <p key={flag.text} className="flag">⚠ {flag.text}</p>
      ))}
    </article>
  )
}

// Small bar chart: one bar per week, taller bar = more commits that week
function CommitChart({ weeks }) {
  const width = 300
  const height = 60
  const most = Math.max(...weeks.map((w) => w.commits))
  const slot = width / weeks.length // horizontal space for each week
  const gap = slot > 4 ? 1 : 0 // no gap when bars are very thin

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Commits per week"
    >
      {weeks.map((w, i) => {
        // Weeks with commits get at least 2px so a single commit is still visible
        const barHeight = w.commits === 0 ? 0 : Math.max(2, (w.commits / most) * height)
        return (
          <rect
            key={w.week}
            x={i * slot + gap / 2}
            y={height - barHeight}
            width={Math.max(slot - gap, 0.5)}
            height={barHeight}
          >
            <title>{`Week of ${w.week}: ${w.commits} commit${w.commits === 1 ? '' : 's'}`}</title>
          </rect>
        )
      })}
    </svg>
  )
}

export default App
