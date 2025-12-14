import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

// Type definitions for export functions
export interface ExportData {
  [key: string]: string | number | boolean | null;
}

/**
 * Converts an array of objects to CSV format
 */
function convertToCSV(data: ExportData[]): string {
  if (data.length === 0) return '';

  // Get headers from the first object
  const headers = Object.keys(data[0]);

  // Escape CSV values (handle commas, quotes, newlines)
  const escapeCSVValue = (value: any): string => {
    if (value === null || value === undefined) return '';
    const stringValue = String(value);
    // If value contains comma, quote, or newline, wrap in quotes and escape quotes
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
  };

  // Create CSV content
  const csvHeaders = headers.join(',');
  const csvRows = data.map(row =>
    headers.map(header => escapeCSVValue(row[header])).join(',')
  );

  return [csvHeaders, ...csvRows].join('\n');
}

/**
 * Downloads a string as a file
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Generates a timestamp for filenames
 */
function getTimestamp(): string {
  const now = new Date();
  return now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

/**
 * Export data to CSV file
 * @param data - Array of objects to export
 * @param filename - Optional filename (without extension), defaults to 'export_[timestamp]'
 */
export function exportToCSV(data: ExportData[], filename?: string): void {
  if (!data || data.length === 0) {
    alert('No data to export');
    return;
  }

  const csvContent = convertToCSV(data);
  const finalFilename = filename
    ? `${filename}_${getTimestamp()}.csv`
    : `export_${getTimestamp()}.csv`;

  downloadFile(csvContent, finalFilename, 'text/csv;charset=utf-8;');
}

/**
 * Export a Chart.js chart to PNG image
 * @param chartCanvas - The canvas element containing the chart
 * @param filename - Optional filename (without extension), defaults to 'chart_[timestamp]'
 */
export function exportChartToPNG(chartCanvas: HTMLCanvasElement | null, filename?: string): void {
  if (!chartCanvas) {
    alert('Chart not found');
    return;
  }

  try {
    // Get the chart as base64 image
    const imageData = chartCanvas.toDataURL('image/png');

    // Create download link
    const link = document.createElement('a');
    const finalFilename = filename
      ? `${filename}_${getTimestamp()}.png`
      : `chart_${getTimestamp()}.png`;

    link.download = finalFilename;
    link.href = imageData;
    link.click();
  } catch (error) {
    console.error('Error exporting chart:', error);
    alert('Failed to export chart. Please try again.');
  }
}

/**
 * Export a DOM element as PNG using html2canvas
 * @param elementId - The ID of the element to capture
 * @param filename - Optional filename (without extension), defaults to 'screenshot_[timestamp]'
 */
export async function exportElementToPNG(elementId: string, filename?: string): Promise<void> {
  const element = document.getElementById(elementId);

  if (!element) {
    alert('Element not found');
    return;
  }

  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#1A1A1D', // Forge dark background
      scale: 2, // Higher quality
    });

    const imageData = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    const finalFilename = filename
      ? `${filename}_${getTimestamp()}.png`
      : `screenshot_${getTimestamp()}.png`;

    link.download = finalFilename;
    link.href = imageData;
    link.click();
  } catch (error) {
    console.error('Error capturing element:', error);
    alert('Failed to export image. Please try again.');
  }
}

/**
 * Export data to PDF report
 * @param data - Array of objects to include in the PDF
 * @param title - Title of the report
 * @param filename - Optional filename (without extension), defaults to 'report_[timestamp]'
 */
export function exportToPDF(
  data: ExportData[],
  title: string = 'Forge Command Report',
  filename?: string
): void {
  try {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    let yPosition = margin;

    // Add title
    doc.setFontSize(20);
    doc.setTextColor(40);
    doc.text(title, margin, yPosition);
    yPosition += 10;

    // Add timestamp
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, margin, yPosition);
    yPosition += 15;

    // Add data
    if (data && data.length > 0) {
      doc.setFontSize(12);
      doc.setTextColor(40);

      data.forEach((item, index) => {
        // Check if we need a new page
        if (yPosition > pageHeight - margin) {
          doc.addPage();
          yPosition = margin;
        }

        // Add section header
        doc.setFont('helvetica', 'bold');
        doc.text(`Record ${index + 1}`, margin, yPosition);
        yPosition += 7;

        // Add item properties
        doc.setFont('helvetica', 'normal');
        Object.entries(item).forEach(([key, value]) => {
          if (yPosition > pageHeight - margin) {
            doc.addPage();
            yPosition = margin;
          }

          const text = `${key}: ${value}`;
          const lines = doc.splitTextToSize(text, pageWidth - 2 * margin);
          doc.text(lines, margin + 5, yPosition);
          yPosition += 5 * lines.length;
        });

        yPosition += 5; // Space between records
      });
    } else {
      doc.text('No data available', margin, yPosition);
    }

    // Add footer
    const totalPages = doc.internal.pages.length - 1;
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(150);
      doc.text(
        `Page ${i} of ${totalPages} - Forge Command`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      );
    }

    // Save the PDF
    const finalFilename = filename
      ? `${filename}_${getTimestamp()}.pdf`
      : `report_${getTimestamp()}.pdf`;

    doc.save(finalFilename);
  } catch (error) {
    console.error('Error generating PDF:', error);
    alert('Failed to generate PDF. Please try again.');
  }
}

/**
 * Export multiple charts and data to a comprehensive PDF report
 * @param sections - Array of report sections with titles, data, and optional chart canvases
 * @param reportTitle - Main title of the report
 * @param filename - Optional filename (without extension)
 */
export async function exportComprehensivePDF(
  sections: {
    title: string;
    data?: ExportData[];
    chartCanvas?: HTMLCanvasElement;
  }[],
  reportTitle: string = 'Forge Command Report',
  filename?: string
): Promise<void> {
  try {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    let yPosition = margin;

    // Add main title
    doc.setFontSize(24);
    doc.setTextColor(40);
    doc.text(reportTitle, pageWidth / 2, yPosition, { align: 'center' });
    yPosition += 15;

    // Add timestamp
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, pageWidth / 2, yPosition, { align: 'center' });
    yPosition += 20;

    // Process each section
    for (const section of sections) {
      // Check if we need a new page
      if (yPosition > pageHeight - 40) {
        doc.addPage();
        yPosition = margin;
      }

      // Section title
      doc.setFontSize(16);
      doc.setTextColor(0, 163, 255); // Forge blue
      doc.text(section.title, margin, yPosition);
      yPosition += 10;

      // Add chart if provided
      if (section.chartCanvas) {
        try {
          const imgData = section.chartCanvas.toDataURL('image/png');
          const imgWidth = pageWidth - 2 * margin;
          const imgHeight = 80; // Fixed height for charts

          if (yPosition + imgHeight > pageHeight - margin) {
            doc.addPage();
            yPosition = margin;
          }

          doc.addImage(imgData, 'PNG', margin, yPosition, imgWidth, imgHeight);
          yPosition += imgHeight + 10;
        } catch (error) {
          console.error('Error adding chart to PDF:', error);
        }
      }

      // Add data table if provided
      if (section.data && section.data.length > 0) {
        doc.setFontSize(10);
        doc.setTextColor(40);

        // Simple table rendering
        section.data.forEach((item, index) => {
          if (yPosition > pageHeight - 30) {
            doc.addPage();
            yPosition = margin;
          }

          Object.entries(item).forEach(([key, value]) => {
            const text = `${key}: ${value}`;
            const lines = doc.splitTextToSize(text, pageWidth - 2 * margin);
            doc.text(lines, margin + 5, yPosition);
            yPosition += 5;
          });

          yPosition += 3;
        });
      }

      yPosition += 10; // Space between sections
    }

    // Add footer to all pages
    const totalPages = doc.internal.pages.length - 1;
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(150);
      doc.text(
        `Page ${i} of ${totalPages} - ${reportTitle}`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      );
    }

    // Save the PDF
    const finalFilename = filename
      ? `${filename}_${getTimestamp()}.pdf`
      : `report_${getTimestamp()}.pdf`;

    doc.save(finalFilename);
  } catch (error) {
    console.error('Error generating comprehensive PDF:', error);
    alert('Failed to generate PDF report. Please try again.');
  }
}
