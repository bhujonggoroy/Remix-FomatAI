/**
 * Triggers a native browser file download from a Blob with proper object URL disposal.
 */
export function triggerBlobDownload(blob: Blob, defaultFilename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', defaultFilename);
  document.body.appendChild(link);
  link.click();

  // Clean up element and release memory
  setTimeout(() => {
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }, 250);
}

/**
 * Sanitizes a title string into a safe filename.
 */
export function formatFilename(title?: string | null, extension = 'docx'): string {
  const base = (title || 'academic_document')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_\-\s]/g, '')
    .replace(/\s+/g, '_')
    .slice(0, 60);

  const cleanBase = base || 'academic_document';
  return cleanBase.endsWith(`.${extension}`) ? cleanBase : `${cleanBase}.${extension}`;
}
