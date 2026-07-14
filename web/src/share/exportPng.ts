import { toBlob } from 'html-to-image'
import { FORMAT_SPECS, type OverlayFormatId } from './types'

export async function exportOverlayPng(node: HTMLElement, formatId: OverlayFormatId) {
  await document.fonts?.ready
  const format = FORMAT_SPECS[formatId]
  try {
    const blob = await toBlob(node, {
      // Blob- und Data-URLs dürfen nicht um einen Cache-Parameter erweitert werden.
      cacheBust: false,
      pixelRatio: 2,
      width: format.width,
      height: format.height,
      quality: 1,
      backgroundColor: undefined,
      filter: (element) => element.dataset?.overlayExportIgnore !== 'true',
    })
    if (!blob) throw new Error('PNG konnte nicht erstellt werden.')
    return blob
  } catch (cause) {
    if (cause instanceof Error) throw cause
    throw new Error('PNG konnte nicht erstellt werden. Bitte versuche es erneut.')
  }
}

export function downloadPng(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 2000)
}
