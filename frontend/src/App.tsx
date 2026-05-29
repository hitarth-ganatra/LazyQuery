import { FormEvent, useMemo, useState } from 'react'
import axios from 'axios'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

type QueryRequest = {
  prompt: string
  limit: number
  offset: number
}

type ChartSpec = {
  chart_type: 'bar' | 'line' | 'scatter' | 'metric' | 'table'
  x_key?: string
  y_keys: string[]
  title: string
}

type QueryResponse = {
  intent: string
  sql: string
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  chart: ChartSpec
  warnings: string[]
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
})

function App() {
  const [prompt, setPrompt] = useState('Show top 10 customers by revenue this month')
  const [limit, setLimit] = useState(100)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [history, setHistory] = useState<string[]>([])

  const hasRows = (result?.rows?.length ?? 0) > 0
  const metricValue = useMemo(() => {
    if (!result || result.chart.chart_type !== 'metric' || !result.chart.y_keys[0]) {
      return null
    }
    return result.rows?.[0]?.[result.chart.y_keys[0] ?? '']
  }, [result])

  const submitQuery = async (event: FormEvent) => {
    event.preventDefault()
    if (!prompt.trim()) return

    setLoading(true)
    setError('')

    try {
      const payload: QueryRequest = { prompt: prompt.trim(), limit, offset: 0 }
      const response = await api.post<QueryResponse>('/query', payload)
      setResult(response.data)
      setHistory((prev) => [payload.prompt, ...prev.filter((item) => item !== payload.prompt)].slice(0, 8))
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || err.message)
      } else {
        setError('Unknown error while executing query')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="layout">
      <header>
        <h1>LazyQuery</h1>
        <p>Natural language analytics for PostgreSQL datasets.</p>
      </header>

      <section className="workspace">
        <form className="query-form" onSubmit={submitQuery}>
          <label htmlFor="prompt">Ask a question</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="e.g. Compare monthly revenue by region"
            rows={4}
          />
          <div className="controls">
            <label>
              Row limit
              <input
                type="number"
                min={1}
                max={1000}
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value) || 1)}
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? 'Running…' : 'Run query'}
            </button>
          </div>
        </form>

        <aside className="history">
          <h2>History</h2>
          {history.length === 0 ? <p>No queries yet</p> : null}
          <ul>
            {history.map((item) => (
              <li key={item}>
                <button type="button" onClick={() => setPrompt(item)}>
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </section>

      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <section className="results">
          <div className="meta">
            <p>
              <strong>Intent:</strong> {result.intent}
            </p>
            <p>
              <strong>Rows:</strong> {result.row_count}
            </p>
          </div>

          <div className="sql-preview">
            <h3>Generated SQL</h3>
            <pre>{result.sql}</pre>
            {result.warnings.length > 0 && (
              <ul>
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="chart-area">
            <h3>{result.chart.title}</h3>
            {result.chart.chart_type === 'metric' && metricValue !== null ? (
              <div className="metric">{String(metricValue)}</div>
            ) : null}

            {result.chart.chart_type === 'bar' && hasRows && result.chart.x_key && result.chart.y_keys[0] ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={result.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={result.chart.x_key} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey={result.chart.y_keys[0]} fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            ) : null}

            {result.chart.chart_type === 'line' && hasRows && result.chart.x_key && result.chart.y_keys[0] ? (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={result.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={result.chart.x_key} />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey={result.chart.y_keys[0]} stroke="#2563eb" />
                </LineChart>
              </ResponsiveContainer>
            ) : null}

            {result.chart.chart_type === 'scatter' && hasRows && result.chart.x_key && result.chart.y_keys[0] ? (
              <ResponsiveContainer width="100%" height={320}>
                <ScatterChart>
                  <CartesianGrid />
                  <XAxis dataKey={result.chart.x_key} name={result.chart.x_key} />
                  <YAxis dataKey={result.chart.y_keys[0]} name={result.chart.y_keys[0]} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={result.rows} fill="#2563eb" />
                </ScatterChart>
              </ResponsiveContainer>
            ) : null}
          </div>

          <div className="table-area">
            <h3>Table output</h3>
            {result.columns.length === 0 ? (
              <p>No rows returned.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    {result.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, rowIndex) => (
                    <tr key={`${rowIndex}-${result.columns.join('-')}`}>
                      {result.columns.map((column) => (
                        <td key={`${rowIndex}-${column}`}>{String(row[column] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      ) : null}
    </main>
  )
}

export default App
