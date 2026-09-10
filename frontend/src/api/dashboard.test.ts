/** Author: Dev2 | Date: 2026-09-10 | Purpose: Verify F06 dashboard API aggregation and failure propagation. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { getExecutiveSummary } from './dashboard'

afterEach(() => vi.restoreAllMocks())

describe('executive dashboard API adapter', () => {
  it('combines dashboard and monitoring responses without shifting organization dates', async () => {
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url === '/api/dashboard/executive') {
        return {
          data: {
            open_tickets: 5,
            average_resolution_hours: 6.25,
            priority_breakdown: { low: 1, medium: 0, high: 3, critical: 1 },
            ticket_trend: [
              { date: '2026-09-09', created: 2, closed: 1 },
              { date: '2026-09-10', created: 1, closed: 0 },
            ],
          },
        }
      }
      return { data: { ok: 8, warning: 1, critical: 1, unknown: 2 } }
    })

    const result = await getExecutiveSummary()

    expect(get).toHaveBeenCalledWith('/api/dashboard/executive')
    expect(get).toHaveBeenCalledWith('/api/monitoring/summary')
    expect(result).toMatchObject({
      openTickets: 5,
      criticalTickets: 1,
      averageResolutionHours: 6.25,
      monitoring: { ok: 8, warning: 1, critical: 1, unknown: 2 },
      trend: [
        { date: '2026-09-09', label: '09.09', created: 2, closed: 1 },
        { date: '2026-09-10', label: '10.09', created: 1, closed: 0 },
      ],
      problemCategories: [
        { name: 'Высокий приоритет', count: 3 },
        { name: 'Критические', count: 1 },
        { name: 'Низкий приоритет', count: 1 },
      ],
    })
  })

  it('rejects when either required aggregate cannot be loaded', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('API unavailable'))

    await expect(getExecutiveSummary()).rejects.toThrow('API unavailable')
  })
})
