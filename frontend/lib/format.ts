export function fmtCNY(n: number | string, digits = 2) {
  const num = typeof n === 'string' ? Number(n) : n;
  return `¥${(num || 0).toFixed(digits)}`;
}
export function fmtPct(p: number | string, digits = 0) {
  const num = typeof p === 'string' ? Number(p) : p;
  return `${((num || 0) * 100).toFixed(digits)}%`;
}
export function fmtTime(v: string | number | Date) {
  const d = new Date(v);
  return isNaN(d.getTime()) ? '' : d.toLocaleString();
}
export function safeNumber(v: any, def = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : def;
}
