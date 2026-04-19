export type UploadPayload = {
  files: File[]
}

export type UploadService = {
  sendFiles: (payload: UploadPayload) => Promise<void>
}

export const uploadService: UploadService = {
  async sendFiles() {
    // Replace this stub with your API object when the backend contract is ready.
    await new Promise((resolve) => window.setTimeout(resolve, 900))
  },
}
