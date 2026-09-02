/** Author: Dev2 | Date: 2026-09-02 | Purpose: Verify the F04 tickets and attachments API contract. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import {
  closeTicket,
  deleteAttachment,
  getFreshAttachmentUrl,
  getTicketAssignees,
  getTicketById,
  getTickets,
  saveTicket,
  takeTicket,
} from './tickets'

const apiTicket = {
  id: '12345678-1234-1234-1234-123456789abc',
  title: 'Проверить принтер',
  description: 'Не печатает тестовую страницу',
  priority: 'high' as const,
  status: 'new' as const,
  author: { id: 'author-id', full_name: 'Автор Тестовый' },
  assignee: null,
  asset: { id: 'asset-id', inventory_number: 'INV-10001', model: 'Printer 1' },
  resolution: null,
  source: 'web' as const,
  created_at: '2026-09-02T01:00:00Z',
  closed_at: null,
}

const apiAttachment = {
  id: 'attachment-id',
  file_name: 'notes.txt',
  content_type: 'text/plain',
  size_bytes: 25,
  download_url: 'http://127.0.0.1:9000/fresh-link',
  created_at: '2026-09-02T01:05:00Z',
  can_delete: true,
}

describe('tickets API adapter', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('uses server filters and maps the short display identifier', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: { items: [apiTicket], total: 1 } })

    const result = await getTickets({ page: 2, pageSize: 12, status: 'new', priority: 'high', assigneeId: 'engineer-id' })

    expect(get).toHaveBeenCalledWith('/api/tickets', { params: { status: 'new', priority: 'high', assignee_id: 'engineer-id', page: 2, page_size: 12 } })
    expect(result.items[0]).toEqual(expect.objectContaining({ number: 'Заявка 12345678', title: 'Проверить принтер', attachments: [] }))
  })

  it('loads assignees and a ticket with current attachment permissions', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url === '/api/ticket-assignees') return { data: [{ id: 'engineer-id', full_name: 'Инженер Тестовый' }] }
      if (url === `/api/tickets/${apiTicket.id}`) return { data: apiTicket }
      return { data: [apiAttachment] }
    })

    const assignees = await getTicketAssignees()
    const ticket = await getTicketById(apiTicket.id)

    expect(assignees).toEqual([{ id: 'engineer-id', fullName: 'Инженер Тестовый' }])
    expect(ticket.attachments[0]).toEqual(expect.objectContaining({ fileName: 'notes.txt', downloadUrl: apiAttachment.download_url, canDelete: true }))
  })

  it('creates a ticket, assigns it and uploads multipart attachments', async () => {
    const post = vi.spyOn(apiClient, 'post').mockImplementation(async (url) => {
      if (url === '/api/tickets') return { data: apiTicket }
      return { data: apiAttachment }
    })
    const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ data: { ...apiTicket, assignee: { id: 'engineer-id', full_name: 'Инженер Тестовый' } } })
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => url.endsWith('/attachments') ? { data: [apiAttachment] } : { data: apiTicket })
    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })

    const ticket = await saveTicket({ title: ' Проверить принтер ', description: ' Описание ', priority: 'high', assetId: 'asset-id', assigneeId: 'engineer-id' }, [file])

    expect(post).toHaveBeenNthCalledWith(1, '/api/tickets', { title: 'Проверить принтер', description: 'Описание', priority: 'high', asset_id: 'asset-id' })
    expect(patch).toHaveBeenCalledWith(`/api/tickets/${apiTicket.id}`, { assignee_id: 'engineer-id' })
    const uploadCall = post.mock.calls[1]
    expect(uploadCall[0]).toBe(`/api/tickets/${apiTicket.id}/attachments`)
    expect(uploadCall[1]).toBeInstanceOf(FormData)
    expect(uploadCall[2]).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } })
    expect(ticket.attachments).toHaveLength(1)
  })

  it('takes, closes and deletes a ticket attachment through PATCH/DELETE', async () => {
    const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ data: apiTicket })
    const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue({ data: undefined })
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => url.endsWith('/attachments') ? { data: [] } : { data: apiTicket })

    await takeTicket(apiTicket.id, 'engineer-id')
    await closeTicket(apiTicket.id, ' Исправлено ')
    await deleteAttachment(apiTicket.id, 'attachment-id')

    expect(patch).toHaveBeenNthCalledWith(1, `/api/tickets/${apiTicket.id}`, { assignee_id: 'engineer-id', status: 'in_progress' })
    expect(patch).toHaveBeenNthCalledWith(2, `/api/tickets/${apiTicket.id}`, { status: 'done', resolution: 'Исправлено' })
    expect(remove).toHaveBeenCalledWith('/api/attachments/attachment-id')
  })

  it('refreshes the attachment list before returning a download URL', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [apiAttachment] })

    const url = await getFreshAttachmentUrl(apiTicket.id, apiAttachment.id)

    expect(apiClient.get).toHaveBeenCalledWith(`/api/tickets/${apiTicket.id}/attachments`)
    expect(url).toBe(apiAttachment.download_url)
  })
})
