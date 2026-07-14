export function photoBlobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') resolve(reader.result)
      else reject(new Error('Das Aktivitätsfoto konnte nicht geladen werden.'))
    }
    reader.onerror = () => reject(reader.error ?? new Error('Das Aktivitätsfoto konnte nicht geladen werden.'))
    reader.readAsDataURL(blob)
  })
}
