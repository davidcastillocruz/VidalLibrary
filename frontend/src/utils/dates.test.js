import { describe, expect, test } from 'vitest';

import { addDays, formatDay, libraryDay } from './dates';

describe('dates', () => {
  test('the day of the library is the one of Barcelona', () => {
    // 23:30 in UTC is already the next day in Barcelona
    expect(libraryDay(new Date('2026-11-26T23:30:00Z'))).toBe('2026-11-27');
  });

  test('days are added across a month and a change of hour', () => {
    expect(addDays('2026-10-24', 10)).toBe('2026-11-03');
    expect(addDays('2026-11-30', 1)).toBe('2026-12-01');
  });

  test('a day is written in the language of the page', () => {
    expect(formatDay('2026-11-27', 'ca')).toBe('27 de novembre');
    expect(formatDay('2026-11-27', 'en', true)).toBe('November 27, 2026');
  });
});
