import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TransitionSummary } from './TransitionSummary'

describe('TransitionSummary', () => {
  it('renders transition labels with counts', () => {
    render(
      <TransitionSummary
        summary={[
          { from: 'Submitted', to: 'Plan Review', count: 12 },
          { from: 'Pending', to: 'Closed - Complete', count: 5 },
        ]}
        selected={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('Submitted → Plan Review')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Pending → Closed - Complete')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('calls onSelect with from and to when count clicked', () => {
    const onSelect = vi.fn()
    render(
      <TransitionSummary
        summary={[{ from: 'Submitted', to: 'Plan Review', count: 3 }]}
        selected={null}
        onSelect={onSelect}
      />
    )

    fireEvent.click(screen.getByText('3'))
    expect(onSelect).toHaveBeenCalledWith('Submitted', 'Plan Review')
  })

  it('calls onSelect with empty strings when already selected and clicked again', () => {
    const onSelect = vi.fn()
    render(
      <TransitionSummary
        summary={[{ from: 'Submitted', to: 'Plan Review', count: 3 }]}
        selected={{ from: 'Submitted', to: 'Plan Review' }}
        onSelect={onSelect}
      />
    )

    fireEvent.click(screen.getByText('3'))
    expect(onSelect).toHaveBeenCalledWith('', '')
  })

  it('returns null when summary is empty', () => {
    const { container } = render(
      <TransitionSummary
        summary={[]}
        selected={null}
        onSelect={vi.fn()}
      />
    )
    expect(container.firstChild).toBeNull()
  })
})
