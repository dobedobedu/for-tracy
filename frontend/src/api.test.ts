import { describe, it, expect, vi, afterEach } from 'vitest'
import { getKanban } from './api'

afterEach(() => vi.unstubAllGlobals())

describe('selected board reports', () => {
  it('sends community and both date endpoints to the server', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ columns: [] }) })
    vi.stubGlobal('fetch', fetch)
    await getKanban(['Bungalow Walk', 'Shellstone'], '2026-10-01', '2026-09-25')
    const url = new URL(fetch.mock.calls[0][0], 'http://localhost')
    expect(url.searchParams.get('community')).toBe('Bungalow Walk,Shellstone')
    expect(url.searchParams.get('report_date')).toBe('2026-10-01')
    expect(url.searchParams.get('from_date')).toBe('2026-09-25')
  })
})
