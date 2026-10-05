// Regression: backend-marked new permits participate in the Changed view.
import { describe, it, expect } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { KanbanBoard } from './KanbanBoard'

const renderCard = (changed: boolean) => render(
  <KanbanBoard data={{ columns: [{ milestone: 'Application / Review', permits: [{
    record_number: 'RES-NEW-26-001577', address: '2429 WATERFRONT Cir', current_status: 'Plan Review',
    current_milestone: 'Application / Review', changed,
    change_info: changed ? { from_status: 'New Application', to_status: 'Plan Review', is_new: true, is_backward: false, is_tracked_milestone: true } : undefined,
  }] }] }} selectedTransition={null} legendFilter="changed" onLegendFilter={() => {}} />
)

describe('backend new-card contract', () => {
  it('includes a marked new application under Changed and counts it', () => {
    renderCard(true)
    expect(screen.getByText('NEW')).toBeInTheDocument()
    expect(screen.getByText('1 / 1')).toBeInTheDocument()
    const card = screen.getByText('RES-NEW-26-001577').closest('div.relative')
    expect(card?.className).not.toContain('opacity-35')
    cleanup()
  })
  it('dims the same record and reports zero when the backend calls it unchanged', () => {
    renderCard(false)
    expect(screen.queryByText('NEW')).not.toBeInTheDocument()
    expect(screen.getByText('0 / 1')).toBeInTheDocument()
    const card = screen.getByText('RES-NEW-26-001577').closest('div.relative')
    expect(card?.className).toContain('opacity-35')
    cleanup()
  })
})
