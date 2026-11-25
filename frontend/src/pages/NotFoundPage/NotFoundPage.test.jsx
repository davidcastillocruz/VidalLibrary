import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import LanguageProvider from '@/languages/LanguageProvider';

import NotFoundPage from './NotFoundPage';

// A browser in Catalan, the main language
beforeEach(() => {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['ca']);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('NotFoundPage', () => {
  test('says which path doesn\'t exist and leads back to the start', () => {
    const router = createMemoryRouter([{ path: '*', element: <NotFoundPage /> }], { initialEntries: ['/llibres/x'] });
    render(
      <LanguageProvider>
        <RouterProvider router={router} />
      </LanguageProvider>,
    );

    expect(screen.getByText('No hi ha res a /llibres/x.')).toBeTruthy();
    expect(screen.getByRole('link', { name: "Torna a l'inici" }).getAttribute('href')).toBe('/');
  });
});
