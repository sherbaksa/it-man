/** Author: Dev2 | Date: 2026-07-16 | Purpose: Pure management aggregate calculations shared by mocks and tests. */
import type { ExecutiveSummary } from '../types/dashboard'
import type { Ticket } from '../types/ticket'

const categoryRules: Array<[string, RegExp]> = [
  ['Оборудование', /принтер|компьютер|картридж|рабочего места/i],
  ['Сеть и доступ', /сете|wi-fi|доступ/i],
  ['Серверы и сервисы', /сервер|сервис|архив/i],
  ['Программное обеспечение', /антивирус|обновлен|мис/i],
]

const ticketCategory = (ticket: Ticket) => categoryRules.find(([, pattern]) => pattern.test(`${ticket.title} ${ticket.description ?? ''}`))?.[0] ?? 'Прочее'
const dayKey = (value: string) => value.slice(0, 10)

export function buildExecutiveSummary(items: Ticket[]): ExecutiveSummary {
  const active = items.filter((ticket) => ticket.status === 'new' || ticket.status === 'in_progress')
  const completed = items.filter((ticket) => ticket.status === 'done' && ticket.closedAt)
  const averageResolutionHours = completed.length ? completed.reduce((sum, ticket) => sum + (new Date(ticket.closedAt!).getTime() - new Date(ticket.createdAt).getTime()) / 3_600_000, 0) / completed.length : 0
  const anchorTime = items.length ? Math.max(...items.map((ticket) => new Date(ticket.createdAt).getTime())) : Date.now()
  const trend = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(anchorTime)
    date.setUTCDate(date.getUTCDate() - (6 - index))
    const key = date.toISOString().slice(0, 10)
    return { date: key, label: new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit' }).format(date), created: items.filter((ticket) => dayKey(ticket.createdAt) === key).length, closed: items.filter((ticket) => ticket.closedAt && dayKey(ticket.closedAt) === key).length }
  })
  const categories = new Map<string, number>()
  items.forEach((ticket) => { const category = ticketCategory(ticket); categories.set(category, (categories.get(category) ?? 0) + 1) })
  const monitoring = { ok: 18, warning: 1, critical: 0 }

  return {
    openTickets: active.length,
    criticalTickets: active.filter((ticket) => ticket.priority === 'critical').length,
    completedTickets: completed.length,
    averageResolutionHours: Math.round(averageResolutionHours * 10) / 10,
    availabilityPercent: 97,
    monitoring,
    trend,
    problemCategories: Array.from(categories, ([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, 3),
  }
}
