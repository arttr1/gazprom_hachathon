export type UploadPayload = {
  files: File[]
}

export type UploadResult = {
  blob: Blob
  filename: string
}

export type UploadService = {
  sendFiles: (payload: UploadPayload) => Promise<UploadResult>
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const uploadService: UploadService = {
  async sendFiles({ files }) {
    if (files.length === 0) {
      throw new Error('Добавьте хотя бы один PDF-файл')
    }

    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))

    let response: Response
    try {
      response = await fetch(`${API_BASE_URL}/api/passports/extract`, {
        method: 'POST',
        body: formData,
      })
    } catch {
      throw new Error('Сервер недоступен. Проверьте, что backend запущен.')
    }

    if (!response.ok) {
      const message = await readErrorMessage(response)
      throw new Error(message)
    }

    const blob = await response.blob()
    if (blob.size === 0) {
      throw new Error('Сервер вернул пустой XLSX-файл')
    }

    return {
      blob,
      filename: getFilename(response.headers.get('Content-Disposition')),
    }
  },
}

async function readErrorMessage(response: Response) {
  try {
    const payload = await response.json()
    if (typeof payload.detail === 'string') {
      return payload.detail
    }

    return 'Не удалось обработать PDF'
  } catch {
    return 'Не удалось обработать PDF'
  }
}

function getFilename(contentDisposition: string | null) {
  const fallback = 'passport_export.xlsx'
  if (!contentDisposition) {
    return fallback
  }

  const match = contentDisposition.match(/filename="?([^"]+)"?/i)
  return match?.[1] || fallback
}
