import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CommunityFilter } from './CommunityFilter'

const mockCommunities = [
  { name: 'BLUE SHELL', count: 109, permits: [] },
  { name: 'ANTHIRIUM', count: 87, permits: [] },
  { name: 'WATERFRONT', count: 65, permits: [] },
  { name: 'GARDENIA', count: 45, permits: [] },
  { name: 'LANTANA', count: 32, permits: [] },
  { name: 'MAGNOLIA', count: 21, permits: [] },
  { name: 'ORCHID', count: 12, permits: [] },
]

vi.mock('@/api', () => ({
  getCommunities: () => Promise.resolve(mockCommunities),
}))

describe('CommunityFilter', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('shows top 5 communities by default as chips', async () => {
    render(<CommunityFilter selected={[]} onToggle={vi.fn()} onClear={vi.fn()} />)

    expect(await screen.findByText('All')).toBeInTheDocument()
    expect(await screen.findByText('BLUE SHELL (109)')).toBeInTheDocument()
    expect(await screen.findByText('ANTHIRIUM (87)')).toBeInTheDocument()
    expect(await screen.findByText('WATERFRONT (65)')).toBeInTheDocument()
    expect(await screen.findByText('GARDENIA (45)')).toBeInTheDocument()
    expect(await screen.findByText('LANTANA (32)')).toBeInTheDocument()
    expect(screen.queryByText('MAGNOLIA (21)')).not.toBeInTheDocument()
  })

  it('shows +N more button for hidden communities', async () => {
    render(<CommunityFilter selected={[]} onToggle={vi.fn()} onClear={vi.fn()} />)

    expect(await screen.findByText('+2 more')).toBeInTheDocument()
  })

  it('pins a community via vertical dots and it persists', async () => {
    render(<CommunityFilter selected={[]} onToggle={vi.fn()} onClear={vi.fn()} />)
    await screen.findByText('BLUE SHELL (109)')

    const blueShellChip = screen.getByText('BLUE SHELL (109)')
    const dots = blueShellChip.querySelector('span[title="Pin"]')
    expect(dots).toBeTruthy()
    fireEvent.click(dots!)

    const pinned = JSON.parse(localStorage.getItem('fortracy_pinned_communities') || '[]')
    expect(pinned).toContain('BLUE SHELL')
  })

  it('unpins a community via vertical dots and it disappears from chips', async () => {
    localStorage.setItem('fortracy_pinned_communities', JSON.stringify(['BLUE SHELL']))
    render(<CommunityFilter selected={[]} onToggle={vi.fn()} onClear={vi.fn()} />)
    await screen.findByText('BLUE SHELL (109)')

    const blueShellChip = screen.getByText('BLUE SHELL (109)')
    const dots = blueShellChip.querySelector('span[title="Unpin"]')
    expect(dots).toBeTruthy()
    fireEvent.click(dots!)

    await waitFor(() => {
      expect(screen.queryByText('BLUE SHELL (109)')).not.toBeInTheDocument()
    })
  })

  it('multi-selects communities', async () => {
    const onToggle = vi.fn()
    render(<CommunityFilter selected={[]} onToggle={onToggle} onClear={vi.fn()} />)
    const chip = await screen.findByText('BLUE SHELL (109)')

    fireEvent.click(chip)
    expect(onToggle).toHaveBeenCalledWith('BLUE SHELL')
  })

  it('shows selected badges', async () => {
    render(
      <CommunityFilter
        selected={['BLUE SHELL', 'ANTHIRIUM']}
        onToggle={vi.fn()}
        onClear={vi.fn()}
      />
    )
    await screen.findByText('BLUE SHELL (109)')

    expect(screen.getByText('BLUE SHELL ×')).toBeInTheDocument()
    expect(screen.getByText('ANTHIRIUM ×')).toBeInTheDocument()
  })
})
