import { toBlob } from 'html-to-image'
import { FORMAT_SPECS, type OverlayFormatId } from './types'

export async function exportOverlayPng(node: HTMLElement, formatId: OverlayFormatId) {
  await document.fonts.ready
  const format = FORMAT_SPECS[formatId]
  const blob = await toBlob(node, {
    cacheBust: true,
    pixelRatio: 2,
    width: format.width,
    height: format.height,
    quality: 1,
    backgroundColor: undefined,
  })
  if (!blob) throw new Error('PNG konnte nicht erstellt werden.')
  return blob
}

export function downloadPng(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
