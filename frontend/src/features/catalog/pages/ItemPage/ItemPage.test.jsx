import { fireEvent, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { answer, failure, makeItem, READER, renderPage } from '@/test/renderPage';
import { api } from '@/utils/api';

import ItemPage from './ItemPage';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: { get: vi.fn(), post: vi.fn() } }));

const routes = [
  { path: '/items/:id', element: <ItemPage /> },
  { path: '/login', element: <p>login</p> },
];
const detail = makeItem({ synopsis: 'Una noia a la Barcelona dels anys trenta.', language: { id: 'l-ca', name: 'Català' }, genres: [] });

beforeEach(() => {
  api.get.mockImplementation(() => answer(detail));
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe('ItemPage', () => {
  test('a guest reads the work and is sent to sign in to reserve it', async () => {
    renderPage(routes, { path: '/items/i-aloma' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Aloma' })).toBeTruthy();
    expect(screen.getByText('1 de 2 lliures')).toBeTruthy();
    expect(screen.getByText('Una noia a la Barcelona dels anys trenta.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Inicia la sessió per reservar' }).getAttribute('href')).toBe('/login');
  });

  test('a reader reserves a copy and is told where to find it', async () => {
    api.post.mockReturnValue(answer({ message: 'Reservat. Passa a recollir-lo a la biblioteca en 3 dies' }));
    renderPage(routes, { path: '/items/i-aloma', user: READER });

    fireEvent.click(await screen.findByRole('button', { name: 'Reserva un exemplar' }));

    expect(await screen.findByText('Reservat. Passa a recollir-lo a la biblioteca en 3 dies')).toBeTruthy();
    expect(api.post).toHaveBeenCalledWith('/loans', { item_id: 'i-aloma' });
    expect(screen.getByRole('link', { name: 'Mira els teus préstecs' })).toBeTruthy();
  });

  test('the reason of a refused reservation shows', async () => {
    api.post.mockImplementation(() => failure(409, 'Ja tens aquesta obra reservada o en préstec'));
    renderPage(routes, { path: '/items/i-aloma', user: READER });

    fireEvent.click(await screen.findByRole('button', { name: 'Reserva un exemplar' }));

    expect(await screen.findByText('Ja tens aquesta obra reservada o en préstec')).toBeTruthy();
  });

  test('with every copy lent the button is off', async () => {
    api.get.mockImplementation(() => answer({ ...detail, available: 0 }));
    renderPage(routes, { path: '/items/i-aloma', user: READER });

    expect((await screen.findByRole('button', { name: 'Reserva un exemplar' })).getAttribute('aria-disabled')).toBe('true');
    expect(screen.getByText('Ara mateix tots els exemplars són en préstec')).toBeTruthy();
  });

  test('a work that does not exist is the 404', async () => {
    api.get.mockImplementation(() => failure(404, 'Aquesta obra no és al catàleg'));
    renderPage(routes, { path: '/items/nope' });

    expect(await screen.findByText('Aquest volum no és al prestatge')).toBeTruthy();
  });
});
