export function masteryBandColor(score?: number): string {
  if (typeof score !== 'number' || Number.isNaN(score) || score < 0 || score > 1) {
    return '#4F46E5'
  }

  if (score < 0.34) {
    return '#DC2626'
  }
  if (score < 0.67) {
    return '#D97706'
  }
  return '#16A34A'
}

export function masteryPercent(score?: number): number {
  if (typeof score !== 'number' || Number.isNaN(score) || score < 0 || score > 1) {
    return 0
  }
  return Math.round(score * 100)
}
