import { useEffect, useRef, useState } from 'react'
import { createPreviewUrl, isUploadable } from '../model/file-helpers'
import type { UploadQueueItem } from '../model/types'
import { uploadService } from '../../../shared/api/upload-service'

function toQueueItems(files: File[]) {
  return files.filter(isUploadable).map<UploadQueueItem>((file) => ({
    id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
    file,
    previewUrl: createPreviewUrl(file),
    status: 'ready',
  }))
}

export function useUploadQueue() {
  const [items, setItems] = useState<UploadQueueItem[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const itemsRef = useRef<UploadQueueItem[]>([])

  useEffect(() => {
    itemsRef.current = items
  }, [items])

  useEffect(() => {
    return () => {
      itemsRef.current.forEach((item) => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl)
        }
      })
    }
  }, [])

  const addFiles = (fileList: FileList | File[]) => {
    const files = Array.from(fileList)
    const nextItems = toQueueItems(files)

    if (nextItems.length === 0) {
      if (files.length > 0) {
        setUploadError('Можно загрузить только PDF-файлы')
      }

      return
    }

    setUploadError(null)
    setItems((current) => [...current, ...nextItems])
  }

  const removeFile = (id: string) => {
    setItems((current) => {
      const target = current.find((item) => item.id === id)

      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl)
      }

      return current.filter((item) => item.id !== id)
    })
  }

  const clearFiles = () => {
    setItems((current) => {
      current.forEach((item) => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl)
        }
      })

      return []
    })
  }

  const uploadFiles = async () => {
    if (items.length === 0 || isUploading) {
      return
    }

    setUploadError(null)
    setIsUploading(true)
    setItems((current) => current.map((item) => ({ ...item, status: 'uploading' })))

    try {
      const result = await uploadService.sendFiles({ files: items.map((item) => item.file) })
      downloadBlob(result.blob, result.filename)
      clearFiles()
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Не удалось обработать PDF')
    } finally {
      setIsUploading(false)
      setItems((current) => current.map((item) => ({ ...item, status: 'ready' })))
    }
  }

  return {
    items,
    isUploading,
    uploadError,
    addFiles,
    removeFile,
    clearFiles,
    uploadFiles,
  }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
