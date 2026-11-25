import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { answer, makeItem, READER, renderPage } from '@/test/renderPage';
import { api } from '@/utils/api';
import { addDays, libraryDay } from '@/utils/dates';

import MyLoansPage from './MyLoansPage';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: { get: vi.fn(), delete: vi.fn() } }));

const routes = [{ path: '/loans', element: <MyLoansPage /> }];
const today = libraryDay();

function loan(id, status, values = {}) {
  return {
    id,
    status,
    item: makeItem({ id: `i-${id}`, title: `Obra ${id}` }),
    requested_at: '2026-11-20T10:00:00Z',
    pickup_until: null,
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

describe('MyLoansPage', () => {
  test('the loans are grouped by what the reader has to do', async () => {
    api.get.mockReturnValue(
      answer([
        loan('a', 'requested', { pickup_until: '2026-11-23T10:00:00Z' }),
        loan('b', 'active', { due_on: addDays(today, 5) }),
        loan('c', 'active', { due_on: addDays(today, -1) }),
        loan('d', 'returned', { returned_at: '2026-11-01T10:00:00Z' }),
      ]),
    );
    renderPage(routes, { path: '/loans', user: READER });

    expect(await screen.findByText('3 de 3 préstecs oberts')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Per recollir' })).toBeTruthy();
    expect(screen.getByText(/Reservat · recull-lo fins al 23 de novembre/)).toBeTruthy();
    expect(screen.getByText(/^Vençut/)).toBeTruthy();
    expect(screen.getByText('Retornat el 1 de novembre')).toBeTruthy();
  });

  test('a reservation is cancelled and the list asked again', async () => {
    api.get.mockReturnValue(answer([loan('a', 'requested', { pickup_until: '2026-11-23T10:00:00Z' })]));
    api.delete.mockReturnValue(answer({ message: 'Reserva anul·lada' }));
    renderPage(routes, { path: '/loans', user: READER });

    fireEvent.click(await screen.findByRole('button', { name: 'Anul·la la reserva' }));

    expect(await screen.findByText('Reserva anul·lada')).toBeTruthy();
    expect(api.delete).toHaveBeenCalledWith('/loans/a');
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  });

  test('without loans it leads to the catalog', async () => {
    api.get.mockReturnValue(answer([]));
    renderPage(routes, { path: '/loans', user: READER });

    expect(await screen.findByRole('link', { name: 'Explora el catàleg' })).toBeTruthy();
  });
});
