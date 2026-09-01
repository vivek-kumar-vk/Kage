/** Rupee formatting for the Finance telemetry panels — Indian digit
    grouping, with a compact lakh form for tight readouts. */

export function formatINR(n: number): string {
  const absValue = Math.abs(n);
  const formattedValue = absValue.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  return n < 0 ? `-₹${formattedValue}` : `₹${formattedValue}`;
}

export function formatINRCompact(n: number): string {
  const absValue = Math.abs(n);
  if (absValue < 1000) {
    return formatINR(n);
  }
  const lakhValue = absValue / 100000;
  const formattedLakhValue = lakhValue.toLocaleString("en-IN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return n < 0 ? `-₹${formattedLakhValue}L` : `₹${formattedLakhValue}L`;
}
