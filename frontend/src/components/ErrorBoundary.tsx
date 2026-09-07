import { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Global error boundary. Catches render/lifecycle errors anywhere in the
 * tree and renders a Persian (RTL) fallback UI instead of a white screen.
 */

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log for debugging (consider hooking external error tracking in prod)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          className="min-h-screen flex items-center justify-center bg-slate-50 p-4"
          dir="rtl"
        >
          <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h1 className="text-xl font-bold text-slate-800 mb-2">
              خطای غیرمنتظره‌ای رخ داد
            </h1>
            <p className="text-sm text-slate-500 mb-6">
              متأسفانه مشکلی در بارگذاری صفحه پیش آمد. لطفاً دوباره تلاش کنید.

            </p>
            {this.state.error && (
              <p className="text-xs text-slate-400 mb-6 font-mono bg-slate-50 p-2 rounded break-all">
                {this.state.error.message}
              </p>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
              >
                تلاش مجدد
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2.5 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium"
              >
                بارگذاری مجدد صفحه
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}