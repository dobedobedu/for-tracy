import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KanbanBoard } from './KanbanBoard'

const mockData = {
  columns: [
    {
      milestone: 'Application / Review',
      permits: [
        {
          record_number: 'RES-001',
          address: '123 MAIN St',
          current_status: 'Submitted',
          current_milestone: 'Application / Review',
          changed: true,
          change_info: {
            from_status: 'Pending',
            to_status: 'Submitted',
            is_backward: false,
            is_tracked_milestone: false,
          },
        },
      ],
    },
    {
      milestone: 'Closed',
      permits: [
        {
          record_number: 'RES-002',
          address: '456 OAK Ave',
          current_status: 'Closed - Complete',
          current_milestone: 'Closed',
          changed: false,
        },
      ],
    },
  ],
}

describe('KanbanBoard', () => {
  it('renders visible lanes', () => {
    render(
      <KanbanBoard
        data={mockData}
        selectedTransition={null}
        legendFilter={null}
        onLegendFilter={() => {}}
      />
    )

    // Permit cards should be visible
    expect(screen.getByText('123 MAIN St')).toBeInTheDocument()
    expect(screen.getByText('456 OAK Ave')).toBeInTheDocument()
    // Record numbers should be visible
    expect(screen.getByText('RES-001')).toBeInTheDocument()
    expect(screen.getByText('RES-002')).toBeInTheDocument()
  })

  it('shows lane count badges', () => {
    render(
      <KanbanBoard
        data={mockData}
        selectedTransition={null}
        legendFilter={null}
        onLegendFilter={() => {}}
      />
    )

    const badges = screen.getAllByText('1')
    expect(badges.length).toBe(2) // One for each lane
  })

  it('filters by selected transition', () => {
    render(
      <KanbanBoard
        data={mockData}
        selectedTransition={{ from: 'Pending', to: 'Submitted' }}
        legendFilter={null}
        onLegendFilter={() => {}}
      />
    )

    // Should show RES-001 because it changed from Pending to Submitted
    expect(screen.getByText('123 MAIN St')).toBeInTheDocument()
    // Should not show RES-002 because it didn't have that transition
    expect(screen.queryByText('456 OAK Ave')).not.toBeInTheDocument()
  })

  it('filters by different transition showing no matches', () => {
    render(
      <KanbanBoard
        data={mockData}
        selectedTransition={{ from: 'Submitted', to: 'Plan Review' }}
        legendFilter={null}
        onLegendFilter={() => {}}
      />
    )

    // Neither permit matches this transition
    expect(screen.queryByText('123 MAIN St')).not.toBeInTheDocument()
    expect(screen.queryByText('456 OAK Ave')).not.toBeInTheDocument()
  })

  it('renders change dot on changed permits', () => {
    render(
      <KanbanBoard
        data={mockData}
        selectedTransition={null}
        legendFilter={null}
        onLegendFilter={() => {}}
      />
    )

    // Changed permit should show from→to text
    expect(screen.getByText('Pending → Submitted')).toBeInTheDocument()
  })
})
