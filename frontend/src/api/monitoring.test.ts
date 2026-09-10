/** Author: Dev2 | Date: 2026-09-09 | Purpose: Verify real monitoring API mapping, filtering and history ordering. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { getMonitoringHistory, getMonitoringStatus } from './monitoring'

afterEach(() => vi.restoreAllMocks())

describe('monitoring API adapter', () => {
  it('maps, filters and paginates statuses while summarizing the full response', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        items: [
          { id: 'one', host_identifier: 'server/01', status: 'critical', last_value: 'CPU 99%', source: 'zabbix', checked_at: '2026-09-09T03:00:00Z', asset: { id: 'asset-1', inventory_number: 'INV-001', model: 'Server' } },
          { id: 'two', host_identifier: 'pc-02', status: 'ok', last_value: null, source: 'kaspersky', checked_at: '2026-09-09T04:00:00Z', asset: null },
        ],
        total: 2,
      },
    })

    const result = await getMonitoringStatus({ page: 1, pageSize: 6, search: 'inv-001', status: 'critical' })

    expect(get).toHaveBeenCalledWith('/api/monitoring/status')
    expect(result.total).toBe(1)
    expect(result.items[0]).toMatchObject({ hostIdentifier: 'server/01', lastValue: 'CPU 99%', asset: { inventoryNumber: 'INV-001' } })
    expect(result.summary).toEqual({ ok: 1, warning: 0, critical: 1, unknown: 0 })
  })

  it('encodes the host identifier and orders history chronologically', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        host_identifier: 'server/01',
        items: [
          { status: 'critical', last_value: 'Down', checked_at: '2026-09-09T05:00:00Z' },
          { status: 'ok', last_value: null, checked_at: '2026-09-09T03:00:00Z' },
        ],
      },
    })

    const result = await getMonitoringHistory('server/01', '2026-09-08T00:00:00Z', '2026-09-09T06:00:00Z')

    expect(get).toHaveBeenCalledWith('/api/monitoring/status/server%2F01/history', {
      params: { from: '2026-09-08T00:00:00Z', to: '2026-09-09T06:00:00Z' },
    })
    expect(result.map((item) => item.status)).toEqual(['ok', 'critical'])
    expect(result[0]).toMatchObject({ value: 'Нет данных', level: 1 })
  })
})
