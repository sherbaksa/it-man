/** Author: Dev2 | Date: 2026-07-16 | Purpose: Smoke-check leadership aggregate calculations. */
const { buildExecutiveSummary } = await import(new URL('../src/utils/executiveSummary.ts', import.meta.url))

const base = { author: { id: 'u', fullName: 'Пользователь' }, source: 'web', attachments: [], asset: undefined, assignee: undefined, description: undefined, resolution: undefined }
const tickets = [
  { ...base, id: '1', number: 'INC-1', title: 'Недоступен сервер', priority: 'critical', status: 'in_progress', createdAt: '2026-07-15T08:00:00Z' },
  { ...base, id: '2', number: 'INC-2', title: 'Не печатает принтер', priority: 'medium', status: 'done', createdAt: '2026-07-14T08:00:00Z', closedAt: '2026-07-14T12:00:00Z' },
]
const summary = buildExecutiveSummary(tickets)
if (summary.openTickets !== 1 || summary.criticalTickets !== 1 || summary.completedTickets !== 1) throw new Error('Ticket counters are invalid')
if (summary.averageResolutionHours !== 4) throw new Error('SLA calculation is invalid')
if (summary.trend.length !== 7 || summary.problemCategories.length !== 2) throw new Error('Trend or categories are invalid')
console.log('Executive summary validation passed: counters, 4h SLA, categories and 7-day trend.')
