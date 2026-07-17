/** Author: Dev2 | Date: 2026-07-16 | Purpose: Smoke-check ORD workflow, versioning and DOCX generation. */
import { writeFile } from 'node:fs/promises'

globalThis.window = { setTimeout }
const ordersApi = await import(new URL('../src/api/orders.ts', import.meta.url))
const engineer = { id: 'mock-engineer', login: 'engineer', fullName: 'Инженер Тестовый', role: 'Engineer', position: 'IT-инженер', initials: 'ИТ' }
const itHead = { id: 'mock-ithead', login: 'ithead', fullName: 'Руководитель ИТ', role: 'IT-Head', position: 'Руководитель IT', initials: 'РИ' }

const pending = await ordersApi.sendOrderForApproval('order-2', engineer)
if (pending.status !== 'pending_approval') throw new Error('Draft was not sent for approval')
const approved = await ordersApi.approveOrder('order-2', itHead)
if (approved.status !== 'approved' || approved.approver?.id !== itHead.id) throw new Error('Approval failed')
const revised = await ordersApi.saveOrder({ templateId: approved.template.id, fields: approved.fields }, engineer, approved.id)
if (revised.status !== 'draft' || revised.version !== 2) throw new Error('Workflow reset or version increment failed')

const blob = await ordersApi.createOrderDocx(revised)
const signature = new Uint8Array(await blob.arrayBuffer()).slice(0, 2)
if (signature[0] !== 0x50 || signature[1] !== 0x4b || blob.size < 1000) throw new Error('Generated DOCX is invalid')

const purchase = (await ordersApi.getOrders({ page: 1, pageSize: 10, type: 'purchase_request' })).items[0]
const purchaseBlob = await ordersApi.createOrderDocx(purchase)
const purchaseSignature = new Uint8Array(await purchaseBlob.arrayBuffer()).slice(0, 2)
if (purchaseSignature[0] !== 0x50 || purchaseSignature[1] !== 0x4b || purchaseBlob.size < 1000) throw new Error('Purchase request DOCX is invalid')
if (process.env.ORDER_DOCX_OUTPUT) await writeFile(process.env.ORDER_DOCX_OUTPUT, Buffer.from(await purchaseBlob.arrayBuffer()))

console.log(`ORD validation passed: approval, version ${revised.version}, draft reset, generic DOCX ${blob.size} bytes, purchase request DOCX ${purchaseBlob.size} bytes.`)
