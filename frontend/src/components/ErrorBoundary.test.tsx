import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

function ThrowingChild(): ReactNode {
  throw new Error('boom');
}

describe('ErrorBoundary', () => {
  let errorSpy: ReturnType<typeof vi.spyOn> | null = null;

  afterEach(() => {
    errorSpy?.mockRestore();
    errorSpy = null;
  });

  it('renders children normally when nothing throws', () => {
    render(
      <ErrorBoundary>
        <div>سلام</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText('سلام')).toBeInTheDocument();
  });

  it('renders the Persian fallback UI when a child throws', () => {
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('خطای غیرمنتظره\u200Cای رخ داد')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'تلاش مجدد' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'بارگذاری مجدد صفحه' })).toBeInTheDocument();
  });
});