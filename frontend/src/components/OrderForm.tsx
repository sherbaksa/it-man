/** Author: Dev2 | Date: 2026-07-16 | Purpose: Dynamic ORD form generated from a template field schema. */
import { Form, Input, InputNumber, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { orderTemplates } from '../api/orders'
import type { DocumentTemplate, Order, OrderFieldDefinition, OrderFormValues } from '../types/order'

interface OrderFormProps {
  open: boolean
  order?: Order | null
  saving: boolean
  onCancel: () => void
  onSave: (values: OrderFormValues) => Promise<void>
}

function DynamicField({ field }: { field: OrderFieldDefinition }) {
  const rules = field.required ? [{ required: true, message: `Заполните поле «${field.label}»` }] : undefined
  const input = field.type === 'textarea' ? <Input.TextArea rows={4} maxLength={3000} showCount placeholder={field.placeholder} /> : field.type === 'number' ? <InputNumber min={0} style={{ width: '100%' }} placeholder={field.placeholder} /> : field.type === 'select' ? <Select options={field.options?.map((option) => ({ value: option, label: option }))} placeholder="Выберите значение" /> : <Input type={field.type === 'date' ? 'date' : 'text'} placeholder={field.placeholder} />
  return <Form.Item name={['fields', field.key]} label={field.label} rules={rules}>{input}</Form.Item>
}

const templateDefaults = (template: DocumentTemplate) => Object.fromEntries(
  template.fieldSchema
    .filter((field) => field.defaultValue !== undefined)
    .map((field) => [field.key, field.defaultValue]),
)

export default function OrderForm({ open, order, saving, onCancel, onSave }: OrderFormProps) {
  const [form] = Form.useForm<OrderFormValues>()
  const [template, setTemplate] = useState<DocumentTemplate>()

  useEffect(() => {
    if (!open) return
    form.resetFields()
    const selected = order?.template
    setTemplate(selected)
    form.setFieldsValue(order ? { templateId: order.template.id, fields: order.fields } : { fields: {} })
  }, [form, open, order])

  const changeTemplate = (templateId: string) => {
    const selected = orderTemplates.find((item) => item.id === templateId)
    setTemplate(selected)
    form.setFieldValue('fields', selected ? templateDefaults(selected) : {})
  }

  const submit = async () => onSave(await form.validateFields())

  return (
    <Modal title={order ? `Редактирование ${order.number}` : 'Новый документ ОРД'} open={open} onCancel={onCancel} onOk={() => void submit()} confirmLoading={saving} okText="Сохранить черновик" cancelText="Отмена" width={760}>
      <Form form={form} layout="vertical" className="order-form">
        {order && order.status !== 'draft' && <div className="workflow-reset-notice">Редактирование создаст версию {order.version + 1} и вернёт документ в статус «Черновик».</div>}
        <Form.Item name="templateId" label="Шаблон документа" rules={[{ required: true, message: 'Выберите шаблон' }]}><Select disabled={Boolean(order)} placeholder="Выберите вид документа" options={orderTemplates.map((item) => ({ value: item.id, label: item.name }))} onChange={changeTemplate} /></Form.Item>
        {template && <><div className="template-description"><strong>{template.name}</strong><span>{template.description}</span></div><div className="dynamic-order-fields">{template.fieldSchema.map((field) => <DynamicField key={field.key} field={field} />)}</div></>}
      </Form>
    </Modal>
  )
}
