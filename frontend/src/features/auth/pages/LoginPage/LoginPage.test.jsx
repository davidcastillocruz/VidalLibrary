import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { answer, failure, renderPage } from '@/test/renderPage';
import { api } from '@/utils/api';

import LoginPage from './LoginPage';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: { get: vi.fn(), post: vi.fn() } }));

const routes = [
  { path: '/login', element: <LoginPage /> },
  { path: '/loans', element: <p>loans</p> },
  { path: '/', element: <p>home</p> },
];

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

function fill(email, password) {
  fireEvent.change(screen.getByLabelText('Correu electrònic'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('Contrasenya'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: 'Entra' }));
}

describe('LoginPage', () => {
  test('nothing is sent while a field is wrong', () => {
    renderPage(routes, { path: '/login' });

    fill('pau', '');

    expect(screen.getByText('Escriu un correu com nom@exemple.cat')).toBeTruthy();
    expect(screen.getByText('Escriu la contrasenya')).toBeTruthy();
    expect(api.post).not.toHaveBeenCalled();
  });

  test('signing in asks who it is and goes back to the page that sent there', async () => {
    api.post.mockReturnValue(answer({ message: 'ok' }));
    const { router, session } = renderPage(routes, { path: '/login' });
    router.navigate('/login', { state: { from: '/loans' } });

    await waitFor(() => expect(screen.getByLabelText('Correu electrònic')).toBeTruthy());
    fill(' pau@vidal.cat ', 'una-contrasenya-llarga');

    await waitFor(() => expect(router.state.location.pathname).toBe('/loans'));
    expect(api.post).toHaveBeenCalledWith('/auth/login', { email: 'pau@vidal.cat', password: 'una-contrasenya-llarga' });
    expect(session.refresh).toHaveBeenCalled();
  });

  test('a page of another site is never where it goes back to', async () => {
    api.post.mockReturnValue(answer({ message: 'ok' }));
    const { router } = renderPage(routes, { path: '/login' });
    router.navigate('/login', { state: { from: '//evil.test' } });

    await waitFor(() => expect(screen.getByLabelText('Correu electrònic')).toBeTruthy());
    fill('pau@vidal.cat', 'una-contrasenya-llarga');

    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  test('a wrong password shows the reason of the backend', async () => {
    api.post.mockImplementation(() => failure(401, 'El correu o la contrasenya no són correctes'));
    renderPage(routes, { path: '/login' });

    fill('pau@vidal.cat', 'una-altra-contrasenya');

    expect(await screen.findByText('El correu o la contrasenya no són correctes')).toBeTruthy();
  });
});
