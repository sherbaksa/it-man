/** Author: Dev2 | Date: 2026-07-16 | Purpose: In-memory ticket adapter shaped for future ticket and attachment endpoints. */
import { getAssetById } from './assets'
import type { Ticket, TicketAttachment, TicketFilters, TicketFormValues, TicketListResponse, TicketPerson, TicketPriority, TicketStatus } from '../types/ticket'

export const ticketStatusLabels: Record<TicketStatus, string> = { new: 'Новая', in_progress: 'В работе', done: 'Закрыта', rejected: 'Отклонена' }
export const ticketPriorityLabels: Record<TicketPriority, string> = { low: 'Низкий', medium: 'Средний', high: 'Высокий', critical: 'Критический' }
export const ticketAssignees: TicketPerson[] = [
  { id: 'mock-engineer', fullName: 'Инженер Тестовый' },
  { id: 'engineer-2', fullName: 'Инженер Второй' },
  { id: 'mock-ithead', fullName: 'Руководитель ИТ' },
]

const attachmentContent = new Map<string, Blob>()
const demoPng = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='), (character) => character.charCodeAt(0))
const demoAttachment: TicketAttachment = { id: 'attachment-1', fileName: 'printer-photo.png', contentType: 'image/png', sizeBytes: demoPng.byteLength, uploadedBy: { id: 'user-1', fullName: 'Сотрудник 01' }, createdAt: '2026-07-16T01:30:00Z' }
attachmentContent.set(demoAttachment.id, new Blob([demoPng], { type: demoAttachment.contentType }))

let tickets: Ticket[] = [
  { id: 'ticket-1', number: 'INC-1250', title: 'Не печатает принтер в кабинете 205', description: 'Принтер включён, но задания остаются в очереди.', priority: 'high', status: 'new', author: { id: 'user-1', fullName: 'Сотрудник 01' }, asset: { id: 'asset-1', inventoryNumber: 'INV-00231', model: 'HP LaserJet Pro M404dn' }, source: 'web', createdAt: '2026-07-16T01:20:00Z', attachments: [demoAttachment] },
  { id: 'ticket-2', number: 'INC-1249', title: 'Настройка рабочего места врача', description: 'Подключить компьютер, МИС и сетевой принтер.', priority: 'medium', status: 'in_progress', author: { id: 'user-2', fullName: 'Сотрудник 02' }, assignee: ticketAssignees[0], asset: { id: 'asset-12', inventoryNumber: 'INV-00241', model: 'Aquarius Pro P30' }, source: 'max', createdAt: '2026-07-15T23:45:00Z', attachments: [] },
  { id: 'ticket-3', number: 'INC-1248', title: 'Нет доступа к сетевой папке', priority: 'medium', status: 'new', author: { id: 'user-3', fullName: 'Сотрудник 03' }, source: 'max', createdAt: '2026-07-15T06:10:00Z', attachments: [] },
  { id: 'ticket-4', number: 'INC-1247', title: 'Недоступен сервер архива', description: 'Zabbix зафиксировал недоступность узла.', priority: 'critical', status: 'in_progress', author: { id: 'system', fullName: 'Zabbix' }, assignee: ticketAssignees[1], asset: { id: 'asset-6', inventoryNumber: 'INV-00236', model: 'Dell PowerEdge R540' }, source: 'zabbix_auto', createdAt: '2026-07-14T22:05:00Z', attachments: [] },
  { id: 'ticket-5', number: 'INC-1246', title: 'Замена картриджа в бухгалтерии', priority: 'low', status: 'done', author: { id: 'user-4', fullName: 'Сотрудник 04' }, assignee: ticketAssignees[0], source: 'web', createdAt: '2026-07-14T02:00:00Z', closedAt: '2026-07-14T04:35:00Z', resolution: 'Картридж заменён, тестовая печать выполнена.', attachments: [] },
  { id: 'ticket-6', number: 'INC-1245', title: 'Медленно работает компьютер регистратуры', priority: 'high', status: 'in_progress', author: { id: 'user-5', fullName: 'Сотрудник 05' }, assignee: ticketAssignees[2], asset: { id: 'asset-2', inventoryNumber: 'INV-00232', model: 'Aquarius Pro P30' }, source: 'web', createdAt: '2026-07-13T07:25:00Z', attachments: [] },
  { id: 'ticket-7', number: 'INC-1244', title: 'Проверить Wi-Fi на втором этаже', priority: 'medium', status: 'rejected', author: { id: 'user-6', fullName: 'Сотрудник 06' }, source: 'max', createdAt: '2026-07-12T03:15:00Z', resolution: 'Дубликат заявки INC-1239.', attachments: [] },
  { id: 'ticket-8', number: 'INC-1243', title: 'Установить обновление антивируса', priority: 'low', status: 'new', author: { id: 'user-7', fullName: 'Сотрудник 07' }, source: 'web', createdAt: '2026-07-11T05:40:00Z', attachments: [] },
]

const wait = () => new Promise((resolve) => window.setTimeout(resolve, 220))
const nextNumber = () => `INC-${1250 + tickets.filter((ticket) => Number(ticket.number.slice(4)) > 1250).length + 1}`

export async function getTickets(filters: TicketFilters): Promise<TicketListResponse> {
  await wait()
  const search = filters.search?.trim().toLocaleLowerCase('ru')
  const filtered = tickets.filter((ticket) => {
    const matchesSearch = !search || [ticket.number, ticket.title, ticket.description, ticket.author.fullName, ticket.asset?.inventoryNumber].some((value) => value?.toLocaleLowerCase('ru').includes(search))
    return matchesSearch && (!filters.status || ticket.status === filters.status) && (!filters.priority || ticket.priority === filters.priority) && (!filters.assigneeId || ticket.assignee?.id === filters.assigneeId)
  })
  const start = (filters.page - 1) * filters.pageSize
  return { items: filtered.slice(start, start + filters.pageSize), total: filtered.length }
}

export async function saveTicket(values: TicketFormValues, files: File[], id?: string): Promise<Ticket> {
  await wait()
  const existing = tickets.find((ticket) => ticket.id === id)
  const asset = await getAssetById(values.assetId)
  const createdAttachments: TicketAttachment[] = files.map((file, index) => {
    const attachment: TicketAttachment = { id: `attachment-${Date.now()}-${index}`, fileName: file.name, contentType: file.type || 'application/octet-stream', sizeBytes: file.size, uploadedBy: ticketAssignees[0], createdAt: new Date().toISOString() }
    attachmentContent.set(attachment.id, file)
    return attachment
  })
  const next: Ticket = {
    id: existing?.id ?? `ticket-${Date.now()}`, number: existing?.number ?? nextNumber(), title: values.title.trim(), description: values.description?.trim() || undefined,
    priority: values.priority, status: existing?.status ?? 'new', author: existing?.author ?? ticketAssignees[0], assignee: ticketAssignees.find((person) => person.id === values.assigneeId),
    asset: asset ? { id: asset.id, inventoryNumber: asset.inventoryNumber, model: asset.model } : undefined, resolution: existing?.resolution, source: existing?.source ?? 'web',
    createdAt: existing?.createdAt ?? new Date().toISOString(), closedAt: existing?.closedAt, attachments: [...(existing?.attachments ?? []), ...createdAttachments],
  }
  tickets = existing ? tickets.map((ticket) => ticket.id === id ? next : ticket) : [next, ...tickets]
  return next
}

export async function takeTicket(id: string, assignee: TicketPerson): Promise<Ticket> {
  await wait()
  const ticket = tickets.find((item) => item.id === id)!
  const next = { ...ticket, status: 'in_progress' as const, assignee }
  tickets = tickets.map((item) => item.id === id ? next : item)
  return next
}

export async function closeTicket(id: string, resolution: string): Promise<Ticket> {
  await wait()
  if (!resolution.trim()) throw new Error('Укажите решение по заявке')
  const ticket = tickets.find((item) => item.id === id)!
  const next = { ...ticket, status: 'done' as const, resolution: resolution.trim(), closedAt: new Date().toISOString() }
  tickets = tickets.map((item) => item.id === id ? next : item)
  return next
}

export async function deleteAttachment(ticketId: string, attachmentId: string): Promise<Ticket> {
  await wait()
  const ticket = tickets.find((item) => item.id === ticketId)!
  const next = { ...ticket, attachments: ticket.attachments.filter((attachment) => attachment.id !== attachmentId) }
  attachmentContent.delete(attachmentId)
  tickets = tickets.map((item) => item.id === ticketId ? next : item)
  return next
}

export function getAttachmentBlob(id: string): Blob | undefined {
  return attachmentContent.get(id)
}
