/** Author: Dev2 | Date: 2026-07-16 | Purpose: Validate F08 filtering, summary and chronological host history. */
globalThis.window = { setTimeout }
const api = await import(new URL('../src/api/monitoring.ts', import.meta.url))

const all = await api.getMonitoringStatus({ page: 1, pageSize: 20 })
if (all.total !== 8) throw new Error(`Expected 8 monitoring hosts, received ${all.total}`)
if (Object.values(all.summary).reduce((sum, value) => sum + value, 0) !== all.total) throw new Error('Monitoring summary does not match host count')
if (all.summary.critical < 1 || all.summary.unknown < 1) throw new Error('Problem states are missing from demonstration data')

const filtered = await api.getMonitoringStatus({ page: 1, pageSize: 20, status: 'warning', source: 'kaspersky' })
if (filtered.total !== 1 || filtered.items[0].hostIdentifier !== '203.0.113.12') throw new Error('Monitoring filters failed')

const history = await api.getMonitoringHistory('192.0.2.21')
if (history.length < 2 || history.at(-1)?.status !== 'critical') throw new Error('Critical host history failed')
if (history.some((point, index) => index > 0 && new Date(point.timestamp) <= new Date(history[index - 1].timestamp))) throw new Error('Monitoring history is not chronological')

console.log(`F08 validation passed: ${all.total} hosts, ${history.length} history points, filters and summary are valid.`)
