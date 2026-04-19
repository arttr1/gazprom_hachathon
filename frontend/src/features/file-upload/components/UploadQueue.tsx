import { formatFileSize, getFileKindLabel } from '../model/file-helpers'
import type { UploadQueueItem } from '../model/types'

type UploadQueueProps = {
  items: UploadQueueItem[]
  onRemove: (id: string) => void
}

export function UploadQueue({ items, onRemove }: UploadQueueProps) {
  if (items.length === 0) {
    return (
      <div className="queue-empty">
        PDF-документы пока не выбраны.
      </div>
    )
  }

  return (
    <div className="queue-list">
      {items.map((item) => (
        <article className="queue-item" key={item.id}>
          {item.previewUrl ? (
            <img className="queue-preview" src={item.previewUrl} alt={item.file.name} />
          ) : (
            <div className="queue-fallback">{getFileKindLabel(item.file)}</div>
          )}
          <div className="queue-meta">
            <p className="queue-name">{item.file.name}</p>
            <div className="queue-info">
              <span>{formatFileSize(item.file.size)}</span>
              <span>PDF</span>
            </div>
          </div>
          <div>
            <div className={`queue-status${item.status === 'ready' ? ' is-ready' : ''}`}>
              {item.status === 'uploading' ? 'Отправка...' : 'Готов к отправке'}
            </div>
            <button
              className="queue-remove"
              type="button"
              onClick={() => onRemove(item.id)}
              aria-label={`Удалить ${item.file.name}`}
            >
              ×
            </button>
          </div>
        </article>
      ))}
    </div>
  )
}
