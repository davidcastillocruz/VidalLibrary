import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import LanguageProvider from '@/languages/LanguageProvider';
import { useLanguage } from '@/languages/useLanguage';

import NotificationProvider from './NotificationProvider';
import { useNotify } from './useNotify';

// A page with one button per notice it can give, and the languages to switch
function Page({ notices }) {
  const notify = useNotify();
  const { setLanguage } = useLanguage();
  return (
    <>
      {notices.map((notice, index) => (
        <button key={index} type="button" onClick={() => notify(notice)}>
          {`notice ${index}`}
        </button>
      ))}
      <button type="button" onClick={() => setLanguage('ca')}>
        ca
      </button>
      <button type="button" onClick={() => setLanguage('es')}>
        es
      </button>
    </>
  );
}

function open(notices) {
  render(
    <LanguageProvider>
      <NotificationProvider>
        <Page notices={notices} />
      </NotificationProvider>
    </LanguageProvider>,
  );
}

function press(name) {
  fireEvent.click(screen.getByRole('button', { name }));
}

// The texts of the toasts on screen, oldest first
function shown() {
  return screen.queryAllByRole('listitem').map((toast) => toast.textContent);
}

async function wait(ms) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
}

// Its time runs out, and then it fades away: the fade starts once React has rendered the leaving toast
async function waitItOut(ms) {
  await wait(ms);
  await wait(200);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['es']);
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('notifications', () => {
  // A screen reader only reads what changes in a live region that was already there: one that comes with its text is
  // often skipped
  test('the toasts come into a region that speaks politely and is there before them', () => {
    open([{ tone: 'success', text: 'Has cerrado la sesión' }]);
    const region = screen.getByRole('region', { name: 'Notificaciones' });
    expect(region.getAttribute('aria-live')).toBe('polite');

    press('notice 0');

    expect(region.textContent).toContain('Has cerrado la sesión');
  });

  test('a success goes away by itself', async () => {
    open([{ tone: 'success', text: 'Has cerrado la sesión' }]);

    press('notice 0');

    expect(shown()).toEqual(['Has cerrado la sesión']);
    await wait(4400);
    expect(shown()).toHaveLength(1);
    await waitItOut(200);
    expect(shown()).toEqual([]);
  });

  test('an error comes with its title and stays longer', async () => {
    open([{ tone: 'error', title: 'No se ha cerrado la sesión', text: 'Revisa tu conexión.' }]);

    press('notice 0');

    expect(shown()).toEqual(['No se ha cerrado la sesión' + 'Revisa tu conexión.']);
    await wait(6000);
    expect(shown()).toHaveLength(1);
  });

  test('the close button takes it away', async () => {
    open([{ tone: 'success', text: 'Guardado' }]);
    press('notice 0');

    press('Cerrar la notificación');
    await wait(200);

    expect(shown()).toEqual([]);
  });

  test('the pointer over it stops its time', async () => {
    open([{ tone: 'success', text: 'Guardado' }]);
    press('notice 0');

    fireEvent.pointerEnter(screen.getByRole('listitem'));
    await wait(10000);
    expect(shown()).toHaveLength(1);

    fireEvent.pointerLeave(screen.getByRole('listitem'));
    await waitItOut(4600);
    expect(shown()).toEqual([]);
  });

  test('the focus inside keeps it while the pointer comes and goes', async () => {
    open([{ tone: 'success', text: 'Guardado' }]);
    press('notice 0');

    act(() => screen.getByRole('button', { name: 'Cerrar la notificación' }).focus());
    fireEvent.pointerEnter(screen.getByRole('listitem'));
    fireEvent.pointerLeave(screen.getByRole('listitem'));
    await wait(10000);

    expect(shown()).toHaveLength(1);
  });

  test('closed from the keyboard, the focus stays in the notifications', async () => {
    open([{ tone: 'success', text: 'Guardado' }]);
    press('notice 0');
    act(() => screen.getByRole('button', { name: 'Cerrar la notificación' }).focus());

    press('Cerrar la notificación');
    await wait(200);

    expect(shown()).toEqual([]);
    expect(document.activeElement).toBe(screen.getByRole('region', { name: 'Notificaciones' }));
  });

  test('only the last three stay on screen', () => {
    open(['uno', 'dos', 'tres', 'cuatro'].map((text) => ({ tone: 'info', text })));

    ['notice 0', 'notice 1', 'notice 2', 'notice 3'].forEach(press);

    expect(shown()).toEqual(['dos', 'tres', 'cuatro']);
  });

  test('a text in another language than the page is not shown', () => {
    open([{ tone: 'success', text: 'Has cerrado la sesión', language: 'es' }]);
    press('notice 0');

    press('ca');

    expect(shown()).toEqual([]);
  });

  test('its time runs while it is hidden: going back to its language later does not bring it back', async () => {
    open([{ tone: 'success', text: 'Has cerrado la sesión', language: 'es' }]);
    press('notice 0');
    press('ca');

    await waitItOut(4600);
    press('es');

    expect(shown()).toEqual([]);
  });
});
