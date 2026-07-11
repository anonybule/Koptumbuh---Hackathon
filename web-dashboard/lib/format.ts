export function formatRp(n: number | null | undefined): string {
  return `Rp ${(n || 0).toLocaleString('id-ID')}`;
}

export function formatDate(d: string | null | undefined): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return d;
  }
}
