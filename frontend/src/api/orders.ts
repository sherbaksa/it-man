/** Author: Dev2 | Date: 2026-07-16 | Purpose: Local ORD adapter with workflow and valid DOCX rendering. */
import { AlignmentType, Document, HeadingLevel, Packer, Paragraph, Table, TableCell, TableRow, TabStopType, TextRun, WidthType } from 'docx'
import type { AuthUser } from '../types/auth'
import type { DocumentTemplate, Order, OrderEvent, OrderFilters, OrderFormValues, OrderListResponse, OrderStatus, OrderType } from '../types/order'
import type { TicketPerson } from '../types/ticket'

export const orderTypeLabels: Record<OrderType, string> = { purchase_request: 'Заявка на закупку', write_off_act: 'Акт списания', work_order: 'Наряд на работы' }
export const orderStatusLabels: Record<OrderStatus, string> = { draft: 'Черновик', pending_approval: 'На согласовании', approved: 'Согласован', executed: 'Исполнен', rejected: 'Отклонён' }

export const orderTemplates: DocumentTemplate[] = [
  { id: 'template-purchase', name: 'Заявка на закупку оборудования', type: 'purchase_request', description: 'Обоснование и параметры закупки IT-оборудования', fieldSchema: [
    { key: 'recipientTitle', label: 'Должность и организация адресата', type: 'text', required: true, defaultValue: 'Руководителю организации' },
    { key: 'recipientName', label: 'Ф.И.О. адресата', type: 'text', required: true, defaultValue: 'Фамилия И.О.' },
    { key: 'authorPosition', label: 'Должность автора (после «от»)', type: 'text', required: true, defaultValue: 'программиста' },
    { key: 'authorDisplayName', label: 'Ф.И.О. автора для документа', type: 'text', placeholder: 'Если не заполнено, используется имя текущего пользователя' },
    { key: 'department', label: 'Подразделение', type: 'text', required: true, placeholder: 'Например, регистратура' },
    { key: 'itemName', label: 'Наименование оборудования', type: 'text', required: true },
    { key: 'quantity', label: 'Количество', type: 'number', required: true },
    { key: 'estimatedCost', label: 'Ориентировочная стоимость, ₽', type: 'number' },
    { key: 'requiredDate', label: 'Требуемая дата', type: 'date', required: true },
    { key: 'justification', label: 'Обоснование закупки', type: 'textarea', required: true },
  ] },
  { id: 'template-writeoff', name: 'Акт списания оборудования', type: 'write_off_act', description: 'Фиксация причины и заключения о списании актива', fieldSchema: [
    { key: 'inventoryNumber', label: 'Инвентарный номер', type: 'text', required: true, placeholder: 'INV-00000' },
    { key: 'equipmentName', label: 'Наименование оборудования', type: 'text', required: true },
    { key: 'commissionDate', label: 'Дата ввода в эксплуатацию', type: 'date' },
    { key: 'reason', label: 'Причина списания', type: 'select', required: true, options: ['Физический износ', 'Моральное устаревание', 'Неремонтопригодность', 'Утрата'] },
    { key: 'technicalConclusion', label: 'Техническое заключение', type: 'textarea', required: true },
  ] },
  { id: 'template-work', name: 'Наряд на выполнение работ', type: 'work_order', description: 'Планирование технических работ и ответственных', fieldSchema: [
    { key: 'workTitle', label: 'Наименование работ', type: 'text', required: true },
    { key: 'location', label: 'Место проведения', type: 'text', required: true },
    { key: 'plannedDate', label: 'Плановая дата', type: 'date', required: true },
    { key: 'responsibleName', label: 'Ответственный исполнитель', type: 'text', required: true },
    { key: 'safetyRequirements', label: 'Требования безопасности', type: 'textarea' },
    { key: 'workDescription', label: 'Состав работ', type: 'textarea', required: true },
  ] },
]

const author = { id: 'mock-engineer', fullName: 'Инженер Тестовый' }
const approver = { id: 'mock-ithead', fullName: 'Руководитель ИТ' }
const event = (id: string, status: OrderStatus, actorName: string, createdAt: string, comment?: string): OrderEvent => ({ id, status, actorName, createdAt, comment })
let orders: Order[] = [
  { id: 'order-1', number: 'ОРД-2026-018', template: orderTemplates[0], fields: { department: 'Поликлиника', itemName: 'Компьютер Aquarius Pro P30', quantity: 5, estimatedCost: 425000, requiredDate: '2026-08-15', justification: 'Обновление рабочих мест врачей.' }, status: 'pending_approval', author, createdAt: '2026-07-16T02:10:00Z', version: 1, history: [event('e1', 'draft', 'Инженер Тестовый', '2026-07-16T02:10:00Z', 'Документ создан'), event('e2', 'pending_approval', 'Инженер Тестовый', '2026-07-16T03:00:00Z', 'Отправлен на согласование')] },
  { id: 'order-2', number: 'ОРД-2026-017', template: orderTemplates[1], fields: { inventoryNumber: 'INV-00105', equipmentName: 'HP LaserJet P1102', commissionDate: '2016-03-10', reason: 'Неремонтопригодность', technicalConclusion: 'Повреждён узел термозакрепления, ремонт экономически нецелесообразен.' }, status: 'draft', author, createdAt: '2026-07-15T04:25:00Z', version: 1, history: [event('e3', 'draft', 'Инженер Тестовый', '2026-07-15T04:25:00Z', 'Документ создан')] },
  { id: 'order-3', number: 'ОРД-2026-016', template: orderTemplates[2], fields: { workTitle: 'Обслуживание сервера архива', location: 'Серверная', plannedDate: '2026-07-18', responsibleName: 'Инженер Второй', safetyRequirements: 'Согласовать окно обслуживания.', workDescription: 'Диагностика дисковой подсистемы и установка обновлений.' }, status: 'approved', author, approver, createdAt: '2026-07-14T01:15:00Z', approvedAt: '2026-07-15T00:30:00Z', version: 1, history: [event('e4', 'draft', 'Инженер Тестовый', '2026-07-14T01:15:00Z'), event('e5', 'pending_approval', 'Инженер Тестовый', '2026-07-14T05:00:00Z'), event('e6', 'approved', 'Руководитель ИТ', '2026-07-15T00:30:00Z', 'Согласовано')] },
  { id: 'order-4', number: 'ОРД-2026-015', template: orderTemplates[2], fields: { workTitle: 'Обновление антивирусных баз', location: 'Все подразделения', plannedDate: '2026-07-12', responsibleName: 'Инженер Тестовый', workDescription: 'Контроль централизованного обновления.' }, status: 'executed', author, approver, createdAt: '2026-07-10T01:00:00Z', approvedAt: '2026-07-10T05:30:00Z', version: 1, history: [event('e7', 'draft', 'Инженер Тестовый', '2026-07-10T01:00:00Z'), event('e8', 'pending_approval', 'Инженер Тестовый', '2026-07-10T03:00:00Z'), event('e9', 'approved', 'Руководитель ИТ', '2026-07-10T05:30:00Z'), event('e10', 'executed', 'Инженер Тестовый', '2026-07-12T11:00:00Z', 'Работы выполнены')] },
  { id: 'order-5', number: 'ОРД-2026-014', template: orderTemplates[0], fields: { department: 'Администрация', itemName: 'Ноутбук', quantity: 2, estimatedCost: 220000, requiredDate: '2026-07-30', justification: 'Для выездной работы.' }, status: 'rejected', author, approver, rejectionReason: 'Необходимо уточнить технические характеристики.', createdAt: '2026-07-09T02:20:00Z', version: 1, history: [event('e11', 'draft', 'Инженер Тестовый', '2026-07-09T02:20:00Z'), event('e12', 'pending_approval', 'Инженер Тестовый', '2026-07-09T04:00:00Z'), event('e13', 'rejected', 'Руководитель ИТ', '2026-07-09T06:10:00Z', 'Необходимо уточнить технические характеристики.')] },
]

const wait = () => new Promise((resolve) => window.setTimeout(resolve, 220))
const asPerson = (user: AuthUser): TicketPerson => ({ id: user.id, fullName: user.fullName })
const nextNumber = () => `ОРД-2026-${String(19 + orders.filter((order) => Number(order.number.slice(-3)) >= 19).length).padStart(3, '0')}`

export async function getOrders(filters: OrderFilters): Promise<OrderListResponse> {
  await wait()
  const search = filters.search?.trim().toLocaleLowerCase('ru')
  const filtered = orders.filter((order) => (!search || [order.number, order.template.name, order.author.fullName, ...Object.values(order.fields).map(String)].some((value) => value.toLocaleLowerCase('ru').includes(search))) && (!filters.status || order.status === filters.status) && (!filters.type || order.template.type === filters.type))
  const start = (filters.page - 1) * filters.pageSize
  return { items: filtered.slice(start, start + filters.pageSize), total: filtered.length }
}

export async function saveOrder(values: OrderFormValues, user: AuthUser, id?: string): Promise<Order> {
  await wait()
  const existing = orders.find((order) => order.id === id)
  const template = orderTemplates.find((item) => item.id === values.templateId)!
  const resetWorkflow = existing && existing.status !== 'draft'
  const next: Order = { id: existing?.id ?? `order-${Date.now()}`, number: existing?.number ?? nextNumber(), template, fields: values.fields, status: 'draft', author: existing?.author ?? asPerson(user), createdAt: existing?.createdAt ?? new Date().toISOString(), version: resetWorkflow ? existing.version + 1 : existing?.version ?? 1, history: [...(existing?.history ?? []), ...(resetWorkflow ? [event(`event-${Date.now()}`, 'draft', user.fullName, new Date().toISOString(), 'Изменено: создана новая версия документа')] : existing ? [] : [event(`event-${Date.now()}`, 'draft', user.fullName, new Date().toISOString(), 'Документ создан')])] }
  orders = existing ? orders.map((order) => order.id === id ? next : order) : [next, ...orders]
  return next
}

async function transition(id: string, status: OrderStatus, user: AuthUser, comment?: string): Promise<Order> {
  await wait()
  const current = orders.find((order) => order.id === id)!
  const next: Order = { ...current, status, approver: status === 'approved' || status === 'rejected' ? asPerson(user) : current.approver, approvedAt: status === 'approved' ? new Date().toISOString() : current.approvedAt, rejectionReason: status === 'rejected' ? comment : current.rejectionReason, history: [...current.history, event(`event-${Date.now()}`, status, user.fullName, new Date().toISOString(), comment)] }
  orders = orders.map((order) => order.id === id ? next : order)
  return next
}

export const sendOrderForApproval = (id: string, user: AuthUser) => transition(id, 'pending_approval', user, 'Отправлен на согласование')
export const approveOrder = (id: string, user: AuthUser) => transition(id, 'approved', user, 'Документ согласован')
export const rejectOrder = (id: string, user: AuthUser, reason: string) => transition(id, 'rejected', user, reason)
export const executeOrder = (id: string, user: AuthUser) => transition(id, 'executed', user, 'Документ исполнен')

export async function createOrderDocx(order: Order): Promise<Blob> {
  if (order.template.type === 'purchase_request') return createPurchaseRequestDocx(order)

  const rows = order.template.fieldSchema.map((field) => new TableRow({ children: [new TableCell({ width: { size: 35, type: WidthType.PERCENTAGE }, children: [new Paragraph({ children: [new TextRun({ text: field.label, bold: true })] })] }), new TableCell({ width: { size: 65, type: WidthType.PERCENTAGE }, children: [new Paragraph(String(order.fields[field.key] ?? '—'))] })] }))
  const document = new Document({ sections: [{ children: [new Paragraph({ text: order.template.name, heading: HeadingLevel.TITLE }), new Paragraph({ children: [new TextRun({ text: `${order.number} · версия ${order.version}`, bold: true })] }), new Paragraph(`Статус: ${orderStatusLabels[order.status]}`), new Paragraph(`Автор: ${order.author.fullName}`), new Paragraph(''), new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows }), new Paragraph(''), new Paragraph(`Сформировано в демонстрационном режиме: ${new Intl.DateTimeFormat('ru-RU').format(new Date())}`)] }] })
  return Packer.toBlob(document)
}

const fieldText = (order: Order, key: string, fallback = '') => String(order.fields[key] ?? fallback).trim()
const formatDocumentDate = (value: string | number | undefined = new Date().toISOString()) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat('ru-RU').format(date)
}

async function createPurchaseRequestDocx(order: Order): Promise<Blob> {
  const recipientTitle = fieldText(order, 'recipientTitle', 'Руководителю организации')
  const recipientName = fieldText(order, 'recipientName', 'Фамилия И.О.')
  const authorPosition = fieldText(order, 'authorPosition', 'программиста')
  const authorName = fieldText(order, 'authorDisplayName', order.author.fullName)
  const department = fieldText(order, 'department')
  const itemName = fieldText(order, 'itemName')
  const quantity = fieldText(order, 'quantity')
  const cost = Number(order.fields.estimatedCost)
  const requiredDate = fieldText(order, 'requiredDate')
  const justification = fieldText(order, 'justification')
  const amountClause = Number.isFinite(cost) && cost > 0
    ? ` на общую стоимость ${new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(cost)} руб.`
    : ''
  const quantityClause = quantity ? ` (${quantity} шт.)` : ''
  const purposeClause = department ? ` для нужд ${department}` : ''
  const details = [justification, requiredDate ? `Требуемая дата: ${formatDocumentDate(requiredDate)}.` : ''].filter(Boolean).join(' ')
  const requestText = `Прошу согласовать приобретение ${itemName}${quantityClause}${purposeClause}${amountClause}${amountClause ? '' : '.'}${details ? ` ${details}` : ''}`

  const document = new Document({
    styles: {
      default: {
        document: {
          run: { font: 'Calibri', size: 28 },
          paragraph: { spacing: { before: 0, after: 0 } },
        },
      },
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1134, right: 850, bottom: 1134, left: 1701, header: 708, footer: 708 },
        },
      },
      children: [
        new Paragraph({
          indent: { left: 5245 },
          children: [
            new TextRun(recipientTitle),
            new TextRun({ break: 1, text: recipientName }),
            new TextRun({ break: 1, text: `от ${authorPosition} ${authorName}` }),
          ],
        }),
        new Paragraph(''),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun('Заявление')] }),
        new Paragraph(''),
        new Paragraph(requestText),
        new Paragraph(''),
        new Paragraph(''),
        new Paragraph(''),
        new Paragraph({
          tabStops: [{ type: TabStopType.RIGHT, position: 9000 }],
          children: [
            new TextRun(formatDocumentDate(order.createdAt)),
            new TextRun('\t'),
            new TextRun(`/ ${authorName} /`),
          ],
        }),
      ],
    }],
  })

  return Packer.toBlob(document)
}
