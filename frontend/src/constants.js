export const LOCATIONS = [
  'Worldwide',
  'Europe (all)',
  // Western Europe
  'UK', 'Germany', 'France', 'Italy', 'Spain', 'Netherlands',
  'Switzerland', 'Belgium', 'Austria', 'Portugal', 'Ireland',
  // Nordic
  'Sweden', 'Denmark', 'Finland', 'Norway',
  // Central / Eastern Europe
  'Poland', 'Czech Republic', 'Hungary', 'Romania', 'Greece',
  'Croatia', 'Slovakia', 'Slovenia', 'Bulgaria', 'Estonia',
  'Latvia', 'Lithuania', 'Luxembourg', 'Serbia', 'Turkey',
  // Americas
  'United States', 'Canada', 'Brazil',
  // Asia-Pacific
  'Australia', 'Japan', 'South Korea', 'China', 'Singapore',
  'India', 'New Zealand',
  // Other
  'South Africa', 'Israel',
]

export const POSITION_TYPES = [
  { value: 'phd', label: 'PhD position' },
  { value: 'predoctoral', label: 'Predoctoral' },
  { value: 'postdoc', label: 'Postdoc' },
  { value: 'fellowship', label: 'Fellowship' },
  { value: 'research_staff', label: 'Research staff' },
  { value: 'any', label: 'Any' },
]

export const REC_CONFIG = {
  apply:    { icon: '✅', label: 'Apply',    color: 'text-green-700 bg-green-50 border-green-200' },
  consider: { icon: '🟡', label: 'Consider', color: 'text-yellow-700 bg-yellow-50 border-yellow-200' },
  skip:     { icon: '❌', label: 'Skip',     color: 'text-red-700 bg-red-50 border-red-200' },
}
