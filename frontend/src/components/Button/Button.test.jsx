import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import Button from './Button';

describe('Button', () => {
  // A disabled button loses the focus: one that saves stays enabled, says it is busy and ignores what arrives
  test('while it saves it keeps the focus and ignores the presses', () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button onClick={onClick}>Desa</Button>);
    const button = screen.getByRole('button', { name: 'Desa' });
    button.focus();

    rerender(
      <Button onClick={onClick} loading>
        Desa
      </Button>,
    );
    fireEvent.click(button);

    expect(document.activeElement).toBe(button);
    expect(button.disabled).toBe(false);
    expect(button.getAttribute('aria-busy')).toBe('true');
    expect(onClick).not.toHaveBeenCalled();
  });

  test('a submit pressed while it saves doesn\'t send the form again', () => {
    const onSubmit = vi.fn((event) => event.preventDefault());
    render(
      <form onSubmit={onSubmit}>
        <Button type="submit" loading>
          Entra
        </Button>
      </form>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Entra' }));

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
