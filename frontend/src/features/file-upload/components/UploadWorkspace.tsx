import { UploadDropzone } from './UploadDropzone'
import { UploadQueue } from './UploadQueue'
import { useUploadQueue } from '../hooks/useUploadQueue'

export function UploadWorkspace() {
  const { items, isUploading, uploadError, addFiles, removeFile, clearFiles, uploadFiles } =
    useUploadQueue()

  return (
    <main className="page-shell">
      <section className="upload-card">
        <div className="upload-card__header">
          <div>
            <h1 className="upload-card__title">Обработка паспортов</h1>
            <p className="upload-card__copy">
              Загрузите PDF-паспорта оборудования. Пайплайн извлечет данные и подготовит структурированный результат.
            </p>
          </div>
          <div className="upload-card__count">{items.length}</div>
        </div>

        <UploadDropzone disabled={isUploading} onFilesSelected={addFiles} />
        <UploadQueue items={items} onRemove={removeFile} />
        {uploadError ? <p className="queue-error">{uploadError}</p> : null}

        <div className="queue-footer">
          <button
            className="button button-primary"
            type="button"
            disabled={items.length === 0 || isUploading}
            onClick={() => void uploadFiles()}
          >
            {isUploading ? 'Отправляем...' : 'Отправить'}
          </button>
          <button
            className="button button-secondary"
            type="button"
            disabled={items.length === 0 || isUploading}
            onClick={clearFiles}
          >
            Очистить
          </button>
        </div>
      </section>
    </main>
  )
}
