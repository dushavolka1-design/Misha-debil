'use client';

import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = {
  sectionLabel: string;
  children: ReactNode;
};

type State = {
  error: Error | null;
};

export class SectionErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[${this.props.sectionLabel}]`, error, info);
  }

  override render() {
    if (this.state.error) {
      return (
        <div className="dar-callout dar-callout--danger" role="alert">
          <h2 className="dar-subheading">Раздел «{this.props.sectionLabel}» временно недоступен</h2>
          <p className="dar-muted">
            Произошла ошибка интерфейса. Обновите страницу или вернитесь позже.
          </p>
          <button
            type="button"
            className="dar-btn dar-btn--secondary"
            onClick={() => this.setState({ error: null })}
          >
            Попробовать снова
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
