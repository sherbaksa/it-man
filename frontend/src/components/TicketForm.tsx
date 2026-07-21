/** Author: Dev2 | Date: 2026-07-16 | Purpose: Create/edit ticket form with validated local attachments. */
import { DeleteOutlined, DownloadOutlined, InboxOutlined, PaperClipOutlined } from '@ant-design/icons'
import { Button, Form, Input, Modal, Select, Upload, message } from 'antd'
import { useEffect, useState } from 'react'
import { getAssets } from '../api/assets'
import { ticketAssignees, ticketPriorityLabels } from '../api/tickets'
import type { Ticket, TicketAttachment, TicketFormValues, TicketPriority } from '../types/ticket'
import { MAX_ATTACHMENT_SIZE_MB, validateAttachment } from '../utils/attachmentValidation'

interface TicketFormProps {
  open: boolean
  ticket?: Ticket | null
  saving: boolean
  requesterMode?: boolean
  onCancel: () => void
  onSave: (values: TicketFormValues, files: File[]) => Promise<void>
  onDeleteAttachment: (attachment: TicketAttachment) => Promise<void>
  onDownloadAttachment: (attachment: TicketAttachment) => void
}

const formatSize = (bytes: number) => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} КБ` : `${(bytes / 1024 / 1024).toFixed(1)} МБ`

export default function TicketForm({ open, ticket, saving, requesterMode = false, onCancel, onSave, onDeleteAttachment, onDownloadAttachment }: TicketFormProps) {
  const [form] = Form.useForm<TicketFormValues>()
  const [files, setFiles] = useState<File[]>([])
  const [assetOptions, setAssetOptions] = useState<{ value: string; label: string }[]>([])
  const [assetLoading, setAssetLoading] = useState(false)
  const [messageApi, contextHolder] = message.useMessage()

  useEffect(() => {
    if (!open) return
    form.resetFields()
    form.setFieldsValue(ticket ? { title: ticket.title, description: ticket.description, priority: ticket.priority, assetId: ticket.asset?.id, assigneeId: ticket.assignee?.id } : { title: '', priority: 'medium' })
    setFiles([])
    setAssetOptions(ticket?.asset ? [{ value: ticket.asset.id, label: `${ticket.asset.inventoryNumber} · ${ticket.asset.model ?? 'Без модели'}` }] : [])
  }, [form, open, ticket])

  const searchAssets = async (search: string) => {
    setAssetLoading(true)
    const result = await getAssets({ page: 1, pageSize: 20, search: search || undefined })
    setAssetOptions(result.items.map((asset) => ({ value: asset.id, label: `${asset.inventoryNumber} · ${asset.model ?? 'Без модели'}` })))
    setAssetLoading(false)
  }

  const addFile = (file: File) => {
    const validationError = validateAttachment(file)
    if (validationError) {
      messageApi.error(`${file.name}: ${validationError}`)
      return Upload.LIST_IGNORE
    }
    if (files.some((item) => item.name === file.name && item.size === file.size)) {
      messageApi.warning('Этот файл уже добавлен')
      return Upload.LIST_IGNORE
    }
    setFiles((current) => [...current, file])
    return Upload.LIST_IGNORE
  }

  const submit = async () => {
    const values = await form.validateFields()
    await onSave(values, files)
  }

  return (
    <Modal title={ticket ? `Редактирование ${ticket.number}` : 'Новая заявка'} open={open} onCancel={onCancel} onOk={() => void submit()} confirmLoading={saving} okText="Сохранить" cancelText="Отмена" width={760}>
      {contextHolder}
      <Form form={form} layout="vertical" className="ticket-form">
        <Form.Item name="title" label="Тема" rules={[{ required: true, message: 'Укажите тему заявки' }, { max: 255 }]}><Input placeholder="Кратко опишите проблему" /></Form.Item>
        <Form.Item name="description" label="Описание"><Input.TextArea rows={4} maxLength={3000} showCount placeholder="Что произошло и что уже пробовали сделать" /></Form.Item>
        <div className="ticket-form-grid">
          <Form.Item name="priority" label="Приоритет" rules={[{ required: true }]}><Select options={Object.entries(ticketPriorityLabels).map(([value, label]) => ({ value: value as TicketPriority, label }))} /></Form.Item>
          {!requesterMode && <Form.Item name="assigneeId" label="Исполнитель"><Select allowClear placeholder="Не назначен" options={ticketAssignees.map((person) => ({ value: person.id, label: person.fullName }))} /></Form.Item>}
        </div>
        <Form.Item name="assetId" label="Связанный актив"><Select allowClear showSearch filterOption={false} loading={assetLoading} placeholder="Начните вводить инвентарный номер или модель" options={assetOptions} onSearch={(value) => void searchAssets(value)} onFocus={() => { if (!assetOptions.length) void searchAssets('') }} /></Form.Item>
        <Form.Item label={`Вложения · до ${MAX_ATTACHMENT_SIZE_MB} МБ`} extra="Разрешены изображения, PDF, DOC и DOCX">
          <Upload.Dragger multiple showUploadList={false} beforeUpload={addFile} accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx">
            <p className="ant-upload-drag-icon"><InboxOutlined /></p><p className="ant-upload-text">Перетащите файлы сюда или нажмите для выбора</p>
          </Upload.Dragger>
        </Form.Item>
        {(ticket?.attachments.length || files.length > 0) && <div className="attachment-list">
          {ticket?.attachments.map((attachment) => <div className="attachment-row" key={attachment.id}><PaperClipOutlined /><span><strong>{attachment.fileName}</strong><small>{formatSize(attachment.sizeBytes)}</small></span><Button type="text" aria-label="Скачать" icon={<DownloadOutlined />} onClick={() => onDownloadAttachment(attachment)} /><Button danger type="text" aria-label="Удалить" icon={<DeleteOutlined />} onClick={() => void onDeleteAttachment(attachment)} /></div>)}
          {files.map((file, index) => <div className="attachment-row pending" key={`${file.name}-${file.size}`}><PaperClipOutlined /><span><strong>{file.name}</strong><small>{formatSize(file.size)} · будет загружен после сохранения</small></span><Button danger type="text" aria-label="Убрать" icon={<DeleteOutlined />} onClick={() => setFiles((current) => current.filter((_, fileIndex) => fileIndex !== index))} /></div>)}
        </div>}
      </Form>
    </Modal>
  )
}
