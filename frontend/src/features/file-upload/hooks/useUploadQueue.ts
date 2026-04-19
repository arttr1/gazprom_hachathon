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
    const nextItems = toQueueItems(Array.from(fileList))

    if (nextItems.length === 0) {
      return
    }

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

    setIsUploading(true)
    setItems((current) => current.map((item) => ({ ...item, status: 'uploading' })))

    try {
      await uploadService.sendFiles({ files: items.map((item) => item.file) })
      clearFiles()
    } finally {
      setIsUploading(false)
      setItems((current) => current.map((item) => ({ ...item, status: 'ready' })))
    }
  }

  return {
    items,
    isUploading,
    addFiles,
    removeFile,
    clearFiles,
    uploadFiles,
  }
}
