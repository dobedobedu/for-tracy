import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import type { CompareResult } from './api'
import App from './App'

const api = vi.hoisted(() => ({
  getUploads: vi.fn(), getCompare: vi.fn(), getKanban: vi.fn(),
  getStreetMappings: vi.fn(), deleteUpload: vi.fn(), getCommunities: vi.fn(),
}))
vi.mock('@/api', () => api)
vi.mock('@/components/UploadZone', () => ({ UploadZone: ({ onUpload }: { onUpload: () => void }) => <button onClick={onUpload}>Fixture upload completed</button> }))
vi.mock('@/components/KanbanBoard', () => ({ KanbanBoard: () => <div>Fixture board</div> }))

const uploads = ['2026-10-01', '2026-10-01', '2026-09-25'].map((date, i) => ({
  id: i + 1, filename: `${date}-${i}.csv`, report_date: date,
  row_count_raw: 19, row_count_after_scope: 19, uploaded_at: date,
}))
const comparison = (count: number): CompareResult => ({
  from_report: { date: '2026-09-25', filename: '' }, to_report: { date: '2026-10-01', filename: '' },
  transitions: [], summary: [{ from: 'New Application', to: 'Plan Review', count }],
})

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  api.getUploads.mockResolvedValue(uploads)
  api.getCompare.mockResolvedValue(comparison(1))
  api.getKanban.mockResolvedValue({ columns: [] })
  api.getStreetMappings.mockResolvedValue([])
  api.getCommunities.mockResolvedValue([{ name: 'Shellstone', count: 4, permits: [] }])
})

describe('report snapshot synchronization', () => {
  it('uses distinct dates and refreshes summary, board and counts after a same-date revision', async () => {
    render(<App />)
    await screen.findByText('Shellstone (4)')
    await waitFor(() => expect(api.getCompare).toHaveBeenLastCalledWith('2026-09-25', '2026-10-01'))
    expect(api.getKanban).toHaveBeenLastCalledWith(undefined, '2026-10-01', '2026-09-25')
    const calls = api.getCompare.mock.calls.length
    api.getCompare.mockResolvedValue(comparison(2))
    api.getCommunities.mockResolvedValue([{ name: 'Shellstone', count: 5, permits: [] }])
    fireEvent.click(screen.getByText('Fixture upload completed'))
    await screen.findByText('Shellstone (5)')
    await waitFor(() => expect(api.getCompare.mock.calls.length).toBeGreaterThan(calls))
    expect(screen.getByText('2', { selector: '[data-slot="badge"]' })).toBeInTheDocument()
  })

  it('ignores an old comparison response after the selected report changes', async () => {
    let resolveOld!: (value: CompareResult) => void
    api.getCompare.mockImplementationOnce(() => new Promise<CompareResult>((resolve) => { resolveOld = resolve }))
    render(<App />)
    await waitFor(() => expect(api.getCompare).toHaveBeenCalled())
    api.getCompare.mockResolvedValue(comparison(2))
    fireEvent.click(screen.getByText('2026-10-01-0.csv'))
    await waitFor(() => expect(screen.getByText('2', { selector: '[data-slot="badge"]' })).toBeInTheDocument())
    await act(async () => resolveOld(comparison(9)))
    expect(screen.queryByText('9', { selector: '[data-slot="badge"]' })).not.toBeInTheDocument()
    expect(screen.getByText('2', { selector: '[data-slot="badge"]' })).toBeInTheDocument()
  })
})
