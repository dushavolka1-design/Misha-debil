import type { ReactNode } from 'react';

export function DocumentViewer({
  pageLabel,
  quote,
  children,
  highlight,
}: {
  pageLabel: string;
  quote?: string;
  children?: ReactNode;
  highlight?: { left: string; top: string; width: string; height: string } | null;
}) {
  return (
    <section className="dar-viewer" aria-label="Просмотр документа">
      <div className="dar-viewer__toolbar">
        <strong>{pageLabel}</strong>
        {quote ? <span className="dar-viewer__quote">{quote}</span> : null}
      </div>
      <div className="dar-doc-canvas">
        <div className="dar-doc-page">
          {children ?? <p className="dar-doc-line">Текст фрагмента недоступен в предпросмотре.</p>}
          {highlight ? (
            <div
              className="dar-bbox"
              style={{
                left: highlight.left,
                top: highlight.top,
                width: highlight.width,
                height: highlight.height,
              }}
              aria-hidden="true"
            />
          ) : null}
        </div>
      </div>
    </section>
  );
}
