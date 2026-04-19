const ALLOWED_TYPES = new Set(['application/pdf'])

export function isUploadable(file: File) {
  return ALLOWED_TYPES.has(file.type) || file.name.toLowerCase().endsWith('.pdf')
}

export function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${Math.round(size / 1024)} KB`
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

export function createPreviewUrl(file: File) {
  void file
  return null
}

export function getFileKindLabel(file: File) {
  void file
  return 'PDF'
}
