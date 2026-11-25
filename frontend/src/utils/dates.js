// The days of the library are the ones of Barcelona (loan_rules.py), whatever the clock of the reader
export const LIBRARY_TIME_ZONE = 'Europe/Madrid';

// A day as 2026-11-27, today at the library by default
export function libraryDay(date = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: LIBRARY_TIME_ZONE }).format(date);
}

// 2026-11-27 plus some days, as 2026-11-27 too. At noon: no change of hour can move it to another day
export function addDays(day, days) {
  const date = new Date(`${day}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

// A day (2026-11-27) or a moment (an ISO date-time) written for people: "27 de novembre"
export function formatDay(value, language, withYear = false) {
  const date = value.length === 10 ? new Date(`${value}T12:00:00Z`) : new Date(value);
  return new Intl.DateTimeFormat(language, {
    day: 'numeric',
    month: 'long',
    year: withYear ? 'numeric' : undefined,
    timeZone: value.length === 10 ? 'UTC' : LIBRARY_TIME_ZONE,
  }).format(date);
}
