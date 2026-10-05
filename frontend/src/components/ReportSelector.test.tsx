import { useState } from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ReportSelector } from './ReportSelector'

const uploads = ['2026-10-01', '2026-09-25'].map((date, i) => ({
  id: i + 1, report_date: date, filename: `${date}.csv`,
  row_count_raw: 19, row_count_after_scope: 19, uploaded_at: date,
}))

function Harness({ onSelect }: { onSelect: (from: string, to: string) => void }) {
  const [range, setRange] = useState(['2026-09-25', '2026-10-01'])
  return <ReportSelector uploads={uploads} fromDate={range[0]} toDate={range[1]} onSelect={(from, to) => {
    setRange([from, to]); onSelect(from, to)
  }} />
}

describe('report range selection', () => {
  it('selects both endpoints in the list, in either order', () => {
    const onSelect = vi.fn()
    render(<Harness onSelect={onSelect} />)
    fireEvent.click(screen.getByText('2026-10-01.csv'))
    expect(onSelect).toHaveBeenLastCalledWith('2026-10-01', '2026-10-01')
    fireEvent.click(screen.getByText('2026-09-25.csv'))
    expect(onSelect).toHaveBeenLastCalledWith('2026-09-25', '2026-10-01')
    fireEvent.click(screen.getByText('2026-09-25.csv'))
    fireEvent.click(screen.getByText('2026-10-01.csv'))
    expect(onSelect).toHaveBeenLastCalledWith('2026-09-25', '2026-10-01')
  })

  it('selects a calendar range across months', () => {
    const onSelect = vi.fn()
    render(<Harness onSelect={onSelect} />)
    fireEvent.click(screen.getByRole('button', { name: '1' }))
    fireEvent.click(screen.getByRole('button', { name: '◀' }))
    fireEvent.click(screen.getByRole('button', { name: '25' }))
    expect(onSelect).toHaveBeenLastCalledWith('2026-09-25', '2026-10-01')
  })
})
