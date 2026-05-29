import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
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

type TableInfo = {
  name: string
  columns: string[]
}

type TablesResponse = {
  tables: TableInfo[]
}

type TableRowsResponse = {
  table: string
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  total_rows: number
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

  const [tables, setTables] = useState<TableInfo[]>([])
  const [tableError, setTableError] = useState('')
  const [tableLoading, setTableLoading] = useState(false)
  const [activeTable, setActiveTable] = useState('')
  const [tableResult, setTableResult] = useState<TableRowsResponse | null>(null)
  const [tableLimit, setTableLimit] = useState(100)
  const [filterColumn, setFilterColumn] = useState('')
  const [filterValue, setFilterValue] = useState('')

  const hasRows = (result?.rows?.length ?? 0) > 0
  const metricValue = useMemo(() => {
    if (!result || result.chart.chart_type !== 'metric' || !result.chart.y_keys[0]) {
      return null
    }
    return result.rows?.[0]?.[result.chart.y_keys[0] ?? '']
  }, [result])

  const numericColumns = useMemo(() => {
    if (!result || result.rows.length === 0) return []
    return result.columns.filter((column) => typeof result.rows[0]?.[column] === 'number')
  }, [result])

  const [chartXKey, setChartXKey] = useState('')
  const [chartYKey, setChartYKey] = useState('')

  useEffect(() => {
    if (!result) {
      setChartXKey('')
      setChartYKey('')
      return
    }
    const defaultY = result.chart.y_keys[0] ?? numericColumns[0] ?? ''
    const defaultX = result.chart.x_key ?? result.columns.find((col) => col !== defaultY) ?? result.columns[0] ?? ''
    setChartXKey(defaultX)
    setChartYKey(defaultY)
  }, [result, numericColumns])

  const fetchTableRows = async (tableName: string, options?: { forceClearFilter?: boolean }) => {
    const currentFilterColumn = options?.forceClearFilter ? '' : filterColumn
    const currentFilterValue = options?.forceClearFilter ? '' : filterValue

    setActiveTable(tableName)
    setTableLoading(true)
    setTableError('')

    try {
      const params: Record<string, string | number> = {
        limit: tableLimit,
        offset: 0,
      }
      if (currentFilterColumn && currentFilterValue) {
        params.filter_column = currentFilterColumn
        params.filter_value = currentFilterValue
      }

      const response = await api.get<TableRowsResponse>(`/tables/${tableName}/rows`, { params })
      setTableResult(response.data)
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setTableError(err.response?.data?.detail || err.message)
      } else {
        setTableError('Unknown error while loading table data')
      }
    } finally {
      setTableLoading(false)
    }
  }

  useEffect(() => {
    const loadTables = async () => {
      try {
        const response = await api.get<TablesResponse>('/tables')
        setTables(response.data.tables)
        if (response.data.tables[0]?.name) {
          const firstTable = response.data.tables[0].name
          setActiveTable(firstTable)
          setFilterColumn(response.data.tables[0].columns[0] ?? '')
          await fetchTableRows(firstTable, { forceClearFilter: true })
        }
      } catch (err) {
        if (axios.isAxiosError(err)) {
          setTableError(err.response?.data?.detail || err.message)
        } else {
          setTableError('Unknown error while loading tables')
        }
      }
    }

    void loadTables()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

      <section className="tables-panel">
        <h2>Tables</h2>
        <div className="table-links">
          {tables.map((table) => (
            <button
              key={table.name}
              type="button"
              className={table.name === activeTable ? 'active' : ''}
              onClick={() => {
                setFilterColumn(table.columns[0] ?? '')
                setFilterValue('')
                void fetchTableRows(table.name, { forceClearFilter: true })
              }}
            >
              {table.name}
            </button>
          ))}
        </div>

        <div className="table-filters">
          <label>
            Filter column
            <select
              value={filterColumn}
              onChange={(event) => setFilterColumn(event.target.value)}
              disabled={!activeTable}
            >
              {(tables.find((table) => table.name === activeTable)?.columns ?? []).map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>
          </label>
          <label>
            Contains
            <input
              type="text"
              value={filterValue}
              onChange={(event) => setFilterValue(event.target.value)}
              placeholder="Type to filter"
            />
          </label>
          <label>
            Rows
            <input
              type="number"
              min={1}
              max={1000}
              value={tableLimit}
              onChange={(event) => setTableLimit(Number(event.target.value) || 1)}
            />
          </label>
          <button type="button" onClick={() => activeTable && void fetchTableRows(activeTable)}>
            Apply
          </button>
          <button
            type="button"
            onClick={() => {
              setFilterValue('')
              if (activeTable) {
                void fetchTableRows(activeTable, { forceClearFilter: true })
              }
            }}
          >
            Clear
          </button>
        </div>

        {tableLoading ? <p>Loading table...</p> : null}
        {tableError ? <p className="error">{tableError}</p> : null}
        {tableResult ? (
          <div className="table-area">
            <p>
              Showing {tableResult.row_count} of {tableResult.total_rows} rows from <strong>{tableResult.table}</strong>
            </p>
            {tableResult.columns.length === 0 ? (
              <p>No rows returned.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    {tableResult.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tableResult.rows.map((row, rowIndex) => (
                    <tr key={`${rowIndex}-${tableResult.columns.join('-')}`}>
                      {tableResult.columns.map((column) => (
                        <td key={`${rowIndex}-${column}`}>{String(row[column] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ) : null}
      </section>

      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <section className="results">
          <div className="meta cards">
            <p>
              <strong>Intent:</strong> {result.intent}
            </p>
            <p>
              <strong>Rows retrieved:</strong> {result.row_count}
            </p>
            <p>
              <strong>Columns analyzed:</strong> {result.columns.length}
            </p>
            <p>
              <strong>Numeric metrics:</strong> {numericColumns.length}
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
            {(result.chart.chart_type === 'bar' || result.chart.chart_type === 'line' || result.chart.chart_type === 'scatter') && (
              <div className="chart-controls">
                <label>
                  X axis
                  <select value={chartXKey} onChange={(event) => setChartXKey(event.target.value)}>
                    {result.columns.map((column) => (
                      <option key={column} value={column}>
                        {column}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Y axis
                  <select value={chartYKey} onChange={(event) => setChartYKey(event.target.value)}>
                    {(numericColumns.length > 0 ? numericColumns : result.columns).map((column) => (
                      <option key={column} value={column}>
                        {column}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )}

            {result.chart.chart_type === 'metric' && metricValue !== null ? (
              <div className="metric">{String(metricValue)}</div>
            ) : null}

            {result.chart.chart_type === 'bar' && hasRows && chartXKey && chartYKey ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={result.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={chartXKey} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey={chartYKey} fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            ) : null}

            {result.chart.chart_type === 'line' && hasRows && chartXKey && chartYKey ? (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={result.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={chartXKey} />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey={chartYKey} stroke="#2563eb" />
                </LineChart>
              </ResponsiveContainer>
            ) : null}

            {result.chart.chart_type === 'scatter' && hasRows && chartXKey && chartYKey ? (
              <ResponsiveContainer width="100%" height={320}>
                <ScatterChart>
                  <CartesianGrid />
                  <XAxis dataKey={chartXKey} name={chartXKey} />
                  <YAxis dataKey={chartYKey} name={chartYKey} />
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
