import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import LanguageProvider from '@/languages/LanguageProvider';

import HomePage from './HomePage';

// A browser in Catalan, the main language
beforeEach(() => {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['ca']);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('HomePage', () => {
  test('says which library it is', () => {
    render(
      <LanguageProvider>
        <HomePage />
      </LanguageProvider>,
    );

    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Biblioteca Vidal i Barraquer');
  });
});
