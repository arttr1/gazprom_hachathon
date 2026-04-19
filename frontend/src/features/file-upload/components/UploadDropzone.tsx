import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'

type UploadDropzoneProps = {
  disabled?: boolean
  onFilesSelected: (files: FileList | File[]) => void
}

export function UploadDropzone({
  disabled = false,
  onFilesSelected,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [isActive, setIsActive] = useState(false)

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) {
      return
    }

    onFilesSelected(files)
  }

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files)
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    setIsActive(false)
    handleFiles(event.dataTransfer.files)
  }

  return (
    <label
      className={`upload-dropzone${isActive ? ' is-active' : ''}`}
      onDragEnter={() => setIsActive(true)}
      onDragOver={(event) => {
        event.preventDefault()
        setIsActive(true)
      }}
      onDragLeave={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
          return
        }

        setIsActive(false)
      }}
      onDrop={handleDrop}
    >
      <div className="dropzone-icon" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 16V6M12 6L8.5 9.5M12 6L15.5 9.5M5 18.5H19"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h2 className="dropzone-title">Добавьте PDF-документы</h2>
      <p className="dropzone-copy">
        Перетащите паспорта оборудования сюда или выберите их вручную.
      </p>
      <div className="dropzone-actions">
        <button
          className="button button-primary"
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          Выбрать PDF
        </button>
      </div>
      <p className="dropzone-hint">Только формат PDF</p>
      <input
        ref={inputRef}
        className="dropzone-input"
        type="file"
        multiple
        accept=".pdf,application/pdf"
        disabled={disabled}
        onChange={handleChange}
      />
    </label>
  )
}
