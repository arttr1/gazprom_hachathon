export type UploadStatus = 'ready' | 'uploading'

export type UploadQueueItem = {
  id: string
  file: File
  previewUrl: string | null
  status: UploadStatus
}
