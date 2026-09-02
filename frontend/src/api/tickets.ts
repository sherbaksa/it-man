/** Author: Dev2 | Date: 2026-09-02 | Purpose: Real backend adapter for tickets and attachments. */
import { apiClient } from './client'
import type { components } from './types'
import type {
  Ticket,
  TicketAttachment,
  TicketFilters,
  TicketFormValues,
  TicketListResponse,
  TicketPerson,
  TicketPriority,
  TicketStatus,
} from '../types/ticket'

type ApiAttachment = components['schemas']['AttachmentRead']
type ApiTicket = components['schemas']['TicketRead']
type ApiTicketCreate = components['schemas']['TicketCreate']
type ApiTicketListResponse = components['schemas']['TicketListResponse']
type ApiTicketUpdate = components['schemas']['TicketUpdate']
type ApiTicketAssignee = components['schemas']['TicketAssigneeRead']

export const ticketStatusLabels: Record<TicketStatus, string> = { new: 'Новая', in_progress: 'В работе', done: 'Закрыта', rejected: 'Отклонена' }
export const ticketPriorityLabels: Record<TicketPriority, string> = { low: 'Низкий', medium: 'Средний', high: 'Высокий', critical: 'Критический' }

export function getTicketDisplayId(id: string): string {
  return `Заявка ${id.slice(0, 8)}`
}

function mapAttachment(item: ApiAttachment): TicketAttachment {
  return {
    id: item.id,
    fileName: item.file_name,
    contentType: item.content_type,
    sizeBytes: item.size_bytes,
    downloadUrl: item.download_url,
    createdAt: item.created_at,
    canDelete: item.can_delete,
  }
}

function mapTicket(item: ApiTicket, attachments: TicketAttachment[] = []): Ticket {
  return {
    id: item.id,
    number: getTicketDisplayId(item.id),
    title: item.title,
    description: item.description ?? undefined,
    priority: item.priority,
    status: item.status,
    author: { id: item.author.id, fullName: item.author.full_name },
    assignee: item.assignee ? { id: item.assignee.id, fullName: item.assignee.full_name } : undefined,
    asset: item.asset ? { id: item.asset.id, inventoryNumber: item.asset.inventory_number, model: item.asset.model ?? undefined } : undefined,
    resolution: item.resolution ?? undefined,
    source: item.source,
    createdAt: item.created_at,
    closedAt: item.closed_at ?? undefined,
    attachments,
  }
}

export async function getTickets(filters: TicketFilters): Promise<TicketListResponse> {
  const { data } = await apiClient.get<ApiTicketListResponse>('/api/tickets', {
    params: {
      status: filters.status,
      priority: filters.priority,
      assignee_id: filters.assigneeId,
      page: filters.page,
      page_size: filters.pageSize,
    },
  })
  return { items: data.items.map((item) => mapTicket(item)), total: data.total }
}

export async function getTicketAssignees(): Promise<TicketPerson[]> {
  const { data } = await apiClient.get<ApiTicketAssignee[]>('/api/ticket-assignees')
  return data.map((item) => ({ id: item.id, fullName: item.full_name }))
}

export async function getTicketAttachments(ticketId: string): Promise<TicketAttachment[]> {
  const { data } = await apiClient.get<ApiAttachment[]>(`/api/tickets/${ticketId}/attachments`)
  return data.map(mapAttachment)
}

export async function getTicketById(id: string): Promise<Ticket> {
  const [{ data }, attachments] = await Promise.all([
    apiClient.get<ApiTicket>(`/api/tickets/${id}`),
    getTicketAttachments(id),
  ])
  return mapTicket(data, attachments)
}

async function uploadAttachments(ticketId: string, files: File[]): Promise<void> {
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    await apiClient.post<ApiAttachment>(`/api/tickets/${ticketId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }
}

export async function saveTicket(values: TicketFormValues, files: File[], id?: string, currentAssigneeId?: string): Promise<Ticket> {
  let ticketId = id
  if (ticketId) {
    if (values.assigneeId !== currentAssigneeId) {
      const payload: ApiTicketUpdate = { assignee_id: values.assigneeId ?? null }
      await apiClient.patch<ApiTicket>(`/api/tickets/${ticketId}`, payload)
    }
  } else {
    const payload: ApiTicketCreate = {
      title: values.title.trim(),
      description: values.description?.trim() || null,
      priority: values.priority,
      asset_id: values.assetId || null,
    }
    const { data } = await apiClient.post<ApiTicket>('/api/tickets', payload)
    ticketId = data.id
    if (values.assigneeId) {
      await apiClient.patch<ApiTicket>(`/api/tickets/${ticketId}`, { assignee_id: values.assigneeId })
    }
  }
  await uploadAttachments(ticketId, files)
  return getTicketById(ticketId)
}

export async function takeTicket(id: string, assigneeId: string): Promise<Ticket> {
  await apiClient.patch<ApiTicket>(`/api/tickets/${id}`, { assignee_id: assigneeId, status: 'in_progress' })
  return getTicketById(id)
}

export async function closeTicket(id: string, resolution: string): Promise<Ticket> {
  const value = resolution.trim()
  if (!value) throw new Error('Укажите решение по заявке')
  await apiClient.patch<ApiTicket>(`/api/tickets/${id}`, { status: 'done', resolution: value })
  return getTicketById(id)
}

export async function deleteAttachment(ticketId: string, attachmentId: string): Promise<Ticket> {
  await apiClient.delete(`/api/attachments/${attachmentId}`)
  return getTicketById(ticketId)
}

export async function getFreshAttachmentUrl(ticketId: string, attachmentId: string): Promise<string | undefined> {
  const attachments = await getTicketAttachments(ticketId)
  return attachments.find((item) => item.id === attachmentId)?.downloadUrl
}
