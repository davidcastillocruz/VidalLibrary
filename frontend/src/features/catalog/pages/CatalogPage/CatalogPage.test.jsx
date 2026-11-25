import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { answer, makeItem, renderPage } from '@/test/renderPage';
import { api } from '@/utils/api';

import CatalogPage from './CatalogPage';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: { get: vi.fn(), post: vi.fn() } }));

const routes = [{ path: '/', element: <CatalogPage /> }];

beforeEach(() => {
  api.get.mockImplementation((url) => {
    if (url === '/catalog/items') {
      return answer({ items: [makeItem(), makeItem({ id: 'i-pa', kind: 'film', title: 'Pa negre', available: 0 })], total: 2 });
    }
    if (url === '/catalog/genres') return answer([{ id: 'g-novel', kind: 'book', name: 'Novel·la' }]);
    return answer([{ id: 'l-ca', name: 'Català' }]);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

// The params of the last request of the works
function lastItemsParams() {
  return api.get.mock.calls.filter(([url]) => url === '/catalog/items').at(-1)[1].params;
}

describe('CatalogPage', () => {
  test('shows each work with whether a copy is free', async () => {
    renderPage(routes);

    expect(await screen.findByRole('heading', { name: 'Aloma' })).toBeTruthy();
    expect(screen.getByText('2 obres')).toBeTruthy();
    expect(screen.getByText('1 exemplar lliure')).toBeTruthy();
    expect(screen.getByText('Tots en préstec')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Aloma/ }).getAttribute('href')).toBe('/items/i-aloma');
  });

  test('a kind tab filters the works and keeps it in the address', async () => {
    const { router } = renderPage(routes);
    await screen.findByRole('heading', { name: 'Aloma' });

    fireEvent.click(screen.getByRole('tab', { name: 'Pel·lícules' }));

    await waitFor(() => expect(lastItemsParams()).toEqual({ kind: 'film', sort: 'title', page: 1 }));
    expect(router.state.location.search).toBe('?kind=film');
    expect(screen.getByRole('tab', { name: 'Pel·lícules' }).getAttribute('aria-selected')).toBe('true');
  });

  test('the search asks once the reader stops typing', async () => {
    renderPage(routes);
    await screen.findByRole('heading', { name: 'Aloma' });

    fireEvent.change(screen.getByRole('searchbox', { name: 'Cerca' }), { target: { value: ' rodo ' } });

    await waitFor(() => expect(lastItemsParams()).toEqual({ q: 'rodo', sort: 'title', page: 1 }));
  });

  test('an empty shelf says why', async () => {
    api.get.mockImplementation((url) => (url === '/catalog/items' ? answer({ items: [], total: 0 }) : answer([])));
    renderPage(routes, { path: '/?q=zzz' });

    expect(await screen.findByText('Aquest prestatge és buit')).toBeTruthy();
    expect(screen.getByText(/Cap obra no coincideix amb la cerca/)).toBeTruthy();
  });
});

describe('CatalogPage search', () => {
  // The search waits for the reader to stop typing: a tab chosen meanwhile stays when it arrives
  test('a tab chosen while the search waits is kept', async () => {
    const { router } = renderPage(routes);
    await screen.findByRole('heading', { name: 'Aloma' });

    fireEvent.change(screen.getByRole('searchbox', { name: 'Cerca' }), { target: { value: 'pa' } });
    fireEvent.click(screen.getByRole('tab', { name: 'Pel·lícules' }));

    await waitFor(() => expect(router.state.location.search).toBe('?kind=film&q=pa'));
  });

  // A link or the back button changes the search from outside: the box says what the list shows
  test('the box follows a search changed from outside', async () => {
    const { router } = renderPage(routes, { path: '/?q=pa' });
    expect(screen.getByRole('searchbox', { name: 'Cerca' }).value).toBe('pa');

    await act(() => router.navigate('/'));

    expect(screen.getByRole('searchbox', { name: 'Cerca' }).value).toBe('');
  });
});

describe('CatalogPage loading', () => {
  // A page that stays blank looks broken: while the first page comes, the shelf shows its shape and says it is busy
  test('the shelf shows its shape while the works load', () => {
    api.get.mockImplementation(() => new Promise(() => {}));
    renderPage(routes);

    const shelf = screen.getByRole('list', { name: "S'està carregant" });
    expect(shelf.getAttribute('aria-busy')).toBe('true');
    expect(shelf.children).toHaveLength(12);
  });
});
