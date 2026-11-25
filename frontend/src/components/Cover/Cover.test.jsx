import { fireEvent, render } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { makeItem } from '@/test/renderPage';

import Cover from './Cover';

vi.mock('@/utils/api', () => ({ API_URL: 'http://api.test', api: {} }));

describe('Cover', () => {
  test('a work with a cover shows its image at the address of its version', () => {
    const { container } = render(<Cover item={makeItem({ cover: '3f9a' })} />);

    expect(container.querySelector('img').getAttribute('src')).toBe('http://api.test/catalog/items/i-aloma/cover?v=3f9a');
  });

  test('without one, a cover is drawn with its title, always in the same cloth', () => {
    const first = render(<Cover item={makeItem()} />).container.firstChild;
    const second = render(<Cover item={makeItem()} />).container.firstChild;

    expect(first.textContent).toBe('AlomaMercè Rodoreda');
    expect(first.style.getPropertyValue('--cloth')).toBe(second.style.getPropertyValue('--cloth'));
  });
});

describe('Cover that failed', () => {
  // A cover whose file went missing shows the drawn one, and a new cover (a new version) is tried again
  test('a new version is tried again after one that failed', () => {
    const { container, rerender } = render(<Cover item={makeItem({ cover: 'old' })} />);
    fireEvent.error(container.querySelector('img'));
    expect(container.querySelector('img')).toBeNull();

    rerender(<Cover item={makeItem({ cover: 'new' })} />);

    expect(container.querySelector('img').getAttribute('src')).toContain('?v=new');
  });
});
