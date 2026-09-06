const STATUS_LABELS: Record<string, string> = {
  published: 'Опубликован',
  needs_review: 'Требует проверки',
  draft: 'Черновик',
  approved: 'Подтверждён',
  awaiting_review: 'Ожидает проверки',
  ready: 'Готов',
  processing: 'В обработке',
  quarantined: 'На проверке',
  quarantine: 'На проверке',
  scanning: 'Сканирование',
  clean: 'Проверен',
  rejected: 'Отклонён',
  infected: 'Заражён',
  failed: 'Ошибка',
  expired: 'Истёк срок',
  deleting: 'Удаление',
  deleted: 'Удалён',
  created: 'Создан',
  uploading: 'Загрузка',
  unavailable: 'Шаблон недоступен',
  queued: 'В очереди',
  normalizing: 'Нормализация',
  ocr: 'Распознавание',
  layout: 'Структура',
  extracting: 'Извлечение',
  rules: 'Проверки',
  blocked_for_new: 'Снят с генерации',
  superseded: 'Заменён новой редакцией',
};

const STAGE_LABELS: Record<string, string> = {
  queued: 'Постановка в очередь',
  normalizing: 'Нормализация страниц',
  ocr: 'Распознавание текста',
  layout: 'Определение структуры',
  extracting: 'Извлечение фактов',
  rules: 'Проверка правил',
  ready: 'Готово',
  failed: 'Ошибка',
};

const OUTCOME_LABELS: Record<string, string> = {
  ok: 'Применимо',
  unknown_case: 'Нужны уточнения',
  blocked_freshness: 'Источник устарел',
  not_applicable: 'Не применимо',
};

export function formatStatus(status: string): string {
  const key = status.toLowerCase();
  return STATUS_LABELS[key] ?? OUTCOME_LABELS[key] ?? status.replace(/_/g, ' ');
}

export function formatDocumentState(state: string): string {
  return formatStatus(state);
}

export function formatStage(stage: string): string {
  const key = stage.toLowerCase();
  return STAGE_LABELS[key] ?? formatStatus(stage);
}

export function formatEntityType(entityType: string): string {
  const map: Record<string, string> = {
    'doc.title': 'Название документа',
    'amount.value': 'Сумма',
    'doc.date.sign': 'Дата подписания',
    'doc.date.effective': 'Дата вступления в силу',
    'doc.date.end': 'Срок действия',
    'party.identifier': 'Идентификатор стороны',
    'doc.excerpt': 'Фрагмент текста',
    'doc.extract': 'Распознавание',
    'party.email': 'Электронная почта',
    'party.phone': 'Телефон',
    'party.name': 'ФИО',
    'party.address': 'Адрес',
    'party.role': 'Сторона',
    'analysis.capability': 'Возможности анализа',
  };
  return map[entityType] ?? 'Извлечённый фрагмент';
}

export function formatFindingKind(kind: 'fact' | 'inference' | string): string {
  if (kind === 'fact') return 'Факт из документа';
  if (kind === 'inference') return 'Вывод системы';
  if (kind === 'rule') return 'Проверка правила';
  return kind;
}

export function formatUncertainty(state: string): string {
  const map: Record<string, string> = {
    ok: 'Достаточно данных',
    low_confidence: 'Низкая уверенность',
    ambiguous: 'Неоднозначно',
    insufficient_data: 'Недостаточно данных',
    needs_review: 'Требует проверки',
    uncertain: 'Неопределённо',
  };
  return map[state] ?? formatStatus(state);
}

export function formatChangeType(change: string): string {
  const map: Record<string, string> = {
    added: 'Добавлено',
    removed: 'Удалено',
    changed: 'Изменено',
  };
  return map[change] ?? change;
}

export function formatSeverity(severity: string): string {
  const map: Record<string, string> = {
    info: 'Информация',
    low: 'Низкий',
    medium: 'Средний',
    high: 'Высокий',
  };
  return map[severity] ?? severity;
}

export function formatOutcome(outcome: string): string {
  return OUTCOME_LABELS[outcome] ?? formatStatus(outcome);
}

export function formatSourceState(state: string): string {
  if (state === 'approved') return 'Подтверждён';
  if (state === 'awaiting_review') return 'Ожидает проверки';
  return formatStatus(state);
}
