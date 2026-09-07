import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Toast } from './Toast';

describe('Toast', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  function renderToast(type = 'success') {
    const onClose = vi.fn();
    render(
      <Toast
        toast={{ id: 1, type: type as 'success' | 'error' | 'info', message: 'محموله حذف شد' }}
        onClose={onClose}
      />,
    );
    return { onClose };
  }

  it('renders the message', () => {
    renderToast();
    expect(screen.getByText('محموله حذف شد')).toBeInTheDocument();
  });

  it('calls onClose when the dismiss button is clicked', async () => {
    // user-event needs real timers for its internal advance; run before applying fake timers.
    vi.useRealTimers();
    const { onClose } = renderToast();
    const user = userEvent.setup({ delay: null });
    await user.click(screen.getByRole('button'));
    expect(onClose).toHaveBeenCalledTimes(1);
    vi.useFakeTimers();
  });

  it('auto-dismisses by calling onClose after 4 seconds', () => {
    const { onClose } = renderToast();
    expect(onClose).not.toHaveBeenCalled();
    vi.advanceTimersByTime(4000);
    expect(onClose).toHaveBeenCalledWith(1);
  });
});