// Shared by the three /analytics/* report screens. The charts stay month-bucketed no matter which
// range is picked — a 7/30-day window just renders one or two bars, which is an honest picture of
// how little data a short window holds rather than switching the chart's x-axis under the reader.
// Mirrors ls_shop.api.admin.analytics.RANGE_MONTHS on the server.
export const RANGE_MONTHS = {
  'Last 7 days': 1,
  'Last 30 days': 1,
  'Last 12 months': 12,
  'All time': 36,
}

export function monthsForRange(range) {
  return RANGE_MONTHS[range] ?? RANGE_MONTHS['Last 12 months']
}
