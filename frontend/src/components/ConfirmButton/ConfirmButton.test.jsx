import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import LanguageProvider from '@/languages/LanguageProvider';

import ConfirmButton from './ConfirmButton';

beforeEach(() => {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['ca']);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function open(onConfirm = vi.fn()) {
  render(
    <LanguageProvider>
      <ConfirmButton question="Eliminar-la?" onConfirm={onConfirm}>
        Elimina
      </ConfirmButton>
      <button type="button">Una altra cosa</button>
    </LanguageProvider>,
  );
  return onConfirm;
}

describe('ConfirmButton', () => {
  test('the first press asks and moves the focus to the answer', () => {
    const onConfirm = open();

    fireEvent.click(screen.getByRole('button', { name: 'Elimina' }));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Sí, fes-ho' }));
  });

  test('answering no brings the focus back to the first button', () => {
    open();
    fireEvent.click(screen.getByRole('button', { name: 'Elimina' }));

    fireEvent.click(screen.getByRole('button', { name: 'No' }));

    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Elimina' }));
  });

  test('confirming does it once and the focus comes back', async () => {
    const onConfirm = open(vi.fn().mockResolvedValue(undefined));
    fireEvent.click(screen.getByRole('button', { name: 'Elimina' }));

    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Sí, fes-ho' })));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Elimina' }));
  });

  // Left alone it goes back by itself, without taking the focus from where the user went meanwhile
  test('a question nobody answers goes away without stealing the focus', () => {
    vi.useFakeTimers();
    open();
    fireEvent.click(screen.getByRole('button', { name: 'Elimina' }));
    const elsewhere = screen.getByRole('button', { name: 'Una altra cosa' });
    elsewhere.focus();

    act(() => vi.advanceTimersByTime(5000));

    expect(screen.getByRole('button', { name: 'Elimina' })).toBeTruthy();
    expect(document.activeElement).toBe(elsewhere);
  });
});
