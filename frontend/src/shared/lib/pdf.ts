import { jsPDF } from 'jspdf'

/** Paleta e tipografia compartilhadas por todo PDF gerado no produto, espelhando
 * tokens.css (verde da marca, tom "ink") para manter a mesma identidade do app. */
const INK: [number, number, number] = [17, 17, 17]
const BRAND_GREEN: [number, number, number] = [126, 217, 87]
const MUTED: [number, number, number] = [120, 120, 120]
const ZEBRA: [number, number, number] = [246, 248, 245]
const BORDER: [number, number, number] = [228, 230, 226]

export function createBrandedPdf(title: string, subtitle?: string) {
  const doc = new jsPDF()
  const pageWidth = doc.internal.pageSize.getWidth()

  doc.setFillColor(...INK)
  doc.rect(0, 0, pageWidth, 26, 'F')
  doc.setFillColor(...BRAND_GREEN)
  doc.rect(0, 26, pageWidth, 1, 'F')

  doc.setFont('courier', 'bold')
  doc.setFontSize(8)
  doc.setTextColor(...BRAND_GREEN)
  doc.text('INSTITUTO LIVRE ACESSO', 14, 10)

  doc.setFont('courier', 'bold')
  doc.setFontSize(13)
  doc.setTextColor(255, 255, 255)
  doc.text(title, 14, 19)

  if (subtitle) {
    doc.setFont('courier', 'normal')
    doc.setFontSize(8.5)
    doc.setTextColor(255, 255, 255)
    doc.text(subtitle, pageWidth - 14, 10, { align: 'right' })
  }

  doc.setTextColor(...INK)
  return doc
}

export function addPdfFooter(doc: jsPDF) {
  const pageCount = doc.getNumberOfPages()
  const pageWidth = doc.internal.pageSize.getWidth()
  const pageHeight = doc.internal.pageSize.getHeight()
  const generatedAt = `Gerado em ${new Date().toLocaleDateString('pt-BR')} às ${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`

  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page)
    doc.setDrawColor(...BORDER)
    doc.line(14, pageHeight - 14, pageWidth - 14, pageHeight - 14)
    doc.setFont('courier', 'normal')
    doc.setFontSize(7.5)
    doc.setTextColor(...MUTED)
    doc.text(generatedAt, 14, pageHeight - 9)
    doc.text(`${page}/${pageCount}`, pageWidth - 14, pageHeight - 9, { align: 'right' })
  }
}

export const PDF_TABLE_THEME = {
  headStyles: {
    fillColor: INK,
    textColor: [255, 255, 255] as [number, number, number],
    font: 'courier',
    fontStyle: 'bold' as const,
    fontSize: 9,
    cellPadding: 3.5,
  },
  bodyStyles: {
    font: 'courier',
    fontSize: 9,
    textColor: INK,
    cellPadding: 3.5,
  },
  alternateRowStyles: { fillColor: ZEBRA },
  styles: { lineColor: BORDER, lineWidth: 0.1 },
}
