type Variant = 'analyzer' | 'generator';

const COPY: Record<Variant, { title: string; text: string }> = {
  analyzer: {
    title: 'Как это работает',
    text: 'Загрузите PDF, DOCX или изображение. Сервис извлечёт факты и риски со ссылками на фрагменты. Обработка обычно занимает 1–5 минут. Результат не заменяет юриста или врача.',
  },
  generator: {
    title: 'Как это работает',
    text: 'Выберите шаблон или пройдите мастер. Заполнение доступно только для готовых форм. Государственные бланки появляются после проверки официального источника. Готовый файл нужно проверить вручную.',
  },
};

export function OnboardingPanel({ variant }: { variant: Variant }) {
  const block = COPY[variant];
  return (
    <details className="dar-help">
      <summary>{block.title}</summary>
      <div className="dar-help__body">
        <p>{block.text}</p>
      </div>
    </details>
  );
}
