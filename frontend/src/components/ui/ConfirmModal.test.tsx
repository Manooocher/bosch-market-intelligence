import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmModal } from './ConfirmModal';

function renderModal(props: Partial<Parameters<typeof ConfirmModal>[0]> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ConfirmModal
      isOpen
      title="حذف محموله"
      message="آیا مطمئن هستید؟"
      confirmLabel="حذف"
      cancelLabel="انصراف"
      variant="danger"
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...props}
    />,
  );
  return { onConfirm, onCancel };
}

describe('ConfirmModal', () => {
  it('renders nothing when closed', () => {
    render(
      <ConfirmModal
        isOpen={false}
        title="t"
        message="m"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows the title and message when open', () => {
    renderModal();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('حذف محموله')).toBeInTheDocument();
    expect(screen.getByText('آیا مطمئن هستید؟')).toBeInTheDocument();
  });

  it('calls onCancel when the cancel button is clicked', async () => {
    const user = userEvent.setup();
    const { onCancel } = renderModal();
    await user.click(screen.getByText('انصراف'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onConfirm when the confirm button is clicked', async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderModal();
    await user.click(screen.getByText('حذف'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel on Escape when not loading', async () => {
    const user = userEvent.setup();
    const { onCancel } = renderModal();
    await user.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('does not call onCancel on Escape while loading', async () => {
    const user = userEvent.setup();
    const { onCancel } = renderModal({ isLoading: true });
    await user.keyboard('{Escape}');
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('shows loading text on the confirm button while loading and does not fire confirm', async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderModal({ isLoading: true });
    const loadingBtn = screen.getByRole('button', { name: /در حال پردازش/ });
    expect(loadingBtn).toBeInTheDocument();
    await user.click(loadingBtn);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});