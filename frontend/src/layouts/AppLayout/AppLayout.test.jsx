import { screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { renderPage } from '@/test/renderPage';

import AppLayout from './AppLayout';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: { get: vi.fn(), post: vi.fn() } }));

afterEach(() => {
  vi.restoreAllMocks();
});

describe('AppLayout', () => {
  // The first Tab reaches it: it skips the header and its sections, straight to what the page is about
  test('the first link skips to the content', () => {
    renderPage([{ element: <AppLayout />, children: [{ path: '/', element: <p>page</p> }] }]);

    const skip = screen.getAllByRole('link')[0];
    expect(skip.textContent).toBe('Salta al contingut');
    expect(skip.getAttribute('href')).toBe('#content');
    expect(document.getElementById('content').textContent).toBe('page');
  });
});
