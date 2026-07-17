/** Author: Dev2 | Date: 2026-07-16 | Purpose: Shared frontend attachment limits matching future backend configuration. */
export const MAX_ATTACHMENT_SIZE_MB = 10
export const allowedAttachmentTypes = [
  'image/jpeg', 'image/png', 'image/webp', 'image/gif',
  'application/pdf', 'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
const allowedExtensions = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf', 'doc', 'docx']

export interface AttachmentCandidate {
  name: string
  size: number
  type: string
}

export function validateAttachment(file: AttachmentCandidate): string | undefined {
  if (file.size > MAX_ATTACHMENT_SIZE_MB * 1024 * 1024) return `Файл превышает лимит ${MAX_ATTACHMENT_SIZE_MB} МБ`
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!allowedAttachmentTypes.includes(file.type) && !allowedExtensions.includes(extension)) return 'Разрешены изображения, PDF, DOC и DOCX'
  return undefined
}
