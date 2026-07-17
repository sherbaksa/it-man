/** Author: Dev2 | Date: 2026-07-16 | Purpose: Smoke-check attachment validation without browser dependencies. */
const { MAX_ATTACHMENT_SIZE_MB, validateAttachment } = await import(new URL('../src/utils/attachmentValidation.ts', import.meta.url))

if (validateAttachment({ name: 'screen.png', size: 1024, type: 'image/png' })) throw new Error('Valid PNG was rejected')
if (!validateAttachment({ name: 'virus.exe', size: 1024, type: 'application/octet-stream' })) throw new Error('Executable file was accepted')
if (!validateAttachment({ name: 'large.pdf', size: (MAX_ATTACHMENT_SIZE_MB + 1) * 1024 * 1024, type: 'application/pdf' })) throw new Error('Oversized file was accepted')

console.log('Ticket attachment validation passed: allowed type, blocked executable, blocked oversized file.')
