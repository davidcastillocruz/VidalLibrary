import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { answer, LIBRARIAN, makeItem, renderPage } from '@/test/renderPage';
import { api } from '@/utils/api';
import { addDays, libraryDay } from '@/utils/dates';

import DeskPage from './DeskPage';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: { get: vi.fn(), post: vi.fn() } }));

const routes = [{ path: '/admin/loans', element: <DeskPage /> }];
const reader = { id: 'u-marta', name: 'Marta Roig', email: 'marta@vidal.cat' };

function loan(id, status, values = {}) {
  return {
    id,
    status,
    reader,
    overdue: false,
    item: makeItem({ id: `i-${id}`, title: `Obra ${id}` }),
    requested_at: '2026-11-20T10:00:00Z',
    pickup_until: '2026-11-23T10:00:00Z',
    picked_up_at: null,
    due_on: null,
    returned_at: null,
    cancelled_at: null,
    ...values,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe('DeskPage', () => {
  test('a reservation is handed over until the usual due day', async () => {
    api.get.mockReturnValue(answer({ loans: [loan('a', 'requested')], total: 1 }));
    api.post.mockReturnValue(answer({ message: 'Préstec lliurat' }));
    renderPage(routes, { path: '/admin/loans', user: LIBRARIAN });

    expect(await screen.findByText('1 préstec')).toBeTruthy();
    expect(screen.getByText(/marta@vidal.cat/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Lliura' }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/admin/loans/a/pickup', { due_on: addDays(libraryDay(), 21) }));
    expect(await screen.findByText('Préstec lliurat')).toBeTruthy();
  });

  test('a loan comes back with one press', async () => {
    api.get.mockReturnValue(answer({ loans: [loan('b', 'active', { due_on: addDays(libraryDay(), 3) })], total: 1 }));
    api.post.mockReturnValue(answer({ message: 'Préstec retornat' }));
    renderPage(routes, { path: '/admin/loans', user: LIBRARIAN });

    fireEvent.click(await screen.findByRole('button', { name: 'Retornat' }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/admin/loans/b/return', undefined));
  });

  test('cancelling a reservation asks first', async () => {
    api.get.mockReturnValue(answer({ loans: [loan('a', 'requested')], total: 1 }));
    api.post.mockReturnValue(answer({ message: 'Reserva anul·lada' }));
    renderPage(routes, { path: '/admin/loans', user: LIBRARIAN });

    fireEvent.click(await screen.findByRole('button', { name: 'Anul·la' }));
    expect(api.post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Sí, fes-ho' }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/admin/loans/a/cancel', undefined));
  });

  test('a filter asks the backend for those loans', async () => {
    api.get.mockReturnValue(answer({ loans: [], total: 0 }));
    renderPage(routes, { path: '/admin/loans', user: LIBRARIAN });
    await screen.findByText('No hi ha cap préstec aquí. Bona feina!');

    fireEvent.click(screen.getByRole('button', { name: 'Vençuts' }));

    await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/admin/loans', { params: { show: 'overdue', page: 1 } }));
  });
});

describe('DeskPage pages', () => {
  // The list shrank under the page (its last loan handed over) or the address is old: back to the last page with rows
  test('a page past the last one goes back to the last', async () => {
    api.get.mockReturnValue(answer({ loans: [], total: 2 }));
    const { router } = renderPage(routes, { path: '/admin/loans?show=requested&page=3', user: LIBRARIAN });

    await waitFor(() => expect(router.state.location.search).toBe('?show=requested'));
  });
});
