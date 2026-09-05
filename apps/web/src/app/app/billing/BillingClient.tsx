'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { Alert, Badge, Button, Checkbox, Disclaimer, ScreenStateView, parseScreenState } from '@dar/ui';
import { getApiBase } from '../../../lib/apiBase';

type LegalItem = {
  id: string;
  consent_id: string;
  consent_version: string;
  content_hash: string;
};

type Plan = {
  plan_code: string;
  price_version: string;
  amount_minor: number;
  currency: string;
  period_days: number;
  trial_days: number;
  label: string;
};

type Subscription = {
  id: string;
  plan_code: string;
  price_version: string;
  amount_minor: number;
  currency: string;
  status: string;
  access_until: string;
  current_period_end: string;
  cancellation_at_period_end: boolean;
  recurring_enabled: boolean;
  next_renewal_at: string | null;
  has_payment_method: boolean;
  trial_ends_at: string | null;
};

type PaymentRow = {
  id: string;
  amount_minor: number;
  currency: string;
  status: string;
  receipt_ref: string | null;
  created_at: string;
};

function formatRub(minor: number): string {
  return `${(minor / 100).toFixed(2)} ₽`;
}

export default function BillingClient() {
  const state = parseScreenState(useSearchParams().get('state'));
  const [recurring, setRecurring] = useState(false);
  const [paymentDoc, setPaymentDoc] = useState<LegalItem | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [selectedPlan, setSelectedPlan] = useState('pro');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [plansRes, meRes] = await Promise.all([
      fetch(`${getApiBase()}/billing/plans`),
      fetch(`${getApiBase()}/billing/me`, { credentials: 'include' }),
    ]);
    if (plansRes.ok) {
      const list = (await plansRes.json()) as Plan[];
      setPlans(list);
    }
    if (meRes.ok) {
      const data = await meRes.json();
      setSub(data.subscription);
      setPayments(data.payments || []);
    }
  }, []);

  useEffect(() => {
    void fetch(`${getApiBase()}/legal/documents/active`)
      .then((r) => r.json())
      .then((items: LegalItem[]) => {
        setPaymentDoc(items.find((i) => i.consent_id === 'payment_recurring') ?? null);
      })
      .catch(() => setPaymentDoc(null));
    void refresh();
  }, [refresh]);

  async function acceptRecurringConsent() {
    if (!paymentDoc) return false;
    const res = await fetch(`${getApiBase()}/privacy/consents/accept`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        consent_id: paymentDoc.consent_id,
        consent_version: paymentDoc.consent_version,
        content_hash: paymentDoc.content_hash,
        locale: 'ru-RU',
      }),
    });
    return res.ok;
  }

  async function subscribe() {
    setErr(null);
    setMsg(null);
    const plan = plans.find((p) => p.plan_code === selectedPlan);
    if (recurring) {
      const ok = await acceptRecurringConsent();
      if (!ok) {
        setErr('Нужно отдельно принять согласие на рекуррентные списания');
        return;
      }
    }
    const res = await fetch(`${getApiBase()}/billing/subscribe`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan_code: selectedPlan,
        enable_recurring: recurring,
        accepted_payment_recurring: recurring,
        client_amount_minor: plan?.amount_minor,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(data?.detail?.detail || data?.detail?.code || 'Ошибка оформления');
      return;
    }
    setMsg(
      data.checkout?.mode === 'trial'
        ? `Trial до ${data.subscription?.trial_ends_at}. Платный переход только при подтверждённом рекурренте.`
        : 'Подписка оформлена (сумма с серверной price table).',
    );
    await refresh();
  }

  async function enableRecurring() {
    if (!sub) return;
    setErr(null);
    const plan = plans.find((p) => p.plan_code === sub.plan_code) || PRICE_FALLBACK(sub);
    const okConsent = await acceptRecurringConsent();
    if (!okConsent) {
      setErr('Нужно отдельно принять payment_recurring');
      return;
    }
    const res = await fetch(`${getApiBase()}/billing/recurring/enable`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        accepted: true,
        shown_amount_minor: plan.amount_minor,
        shown_period_days: plan.period_days,
        shown_next_charge_at: sub.current_period_end,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(data?.detail?.detail || 'Не удалось включить рекуррент');
      return;
    }
    setMsg(
      `Рекуррент: ${formatRub(data.amount_minor)} / ${data.period_days} дн., следующее списание ${data.next_charge_at}. Отмена: ${data.cancel_path}`,
    );
    await refresh();
  }

  async function cancel() {
    setErr(null);
    const res = await fetch(`${getApiBase()}/billing/cancel`, { method: 'POST', credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(data?.detail?.detail || 'Ошибка отмены');
      return;
    }
    setMsg(`${data.message} Доступ до ${data.access_until}.`);
    await refresh();
  }

  async function removePaymentMethod() {
    setErr(null);
    const res = await fetch(`${getApiBase()}/billing/payment-method/remove`, {
      method: 'POST',
      credentials: 'include',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(data?.detail?.detail || 'Ошибка удаления способа оплаты');
      return;
    }
    setMsg(data.message || 'Способ оплаты удалён');
    await refresh();
  }

  return (
    <div>
      <h1 className="dar-page-title">Подписка и платежи</h1>
      <p className="dar-page-lead">
        Цены только с сервера. Production-провайдер не подключается без договора и live credentials. Чеки не
        генерируются фиктивно.
      </p>
      <ScreenStateView
        state={state}
        ready={
          <div className="dar-stack">
            <Disclaimer />
            {err ? (
              <Alert title="Ошибка" tone="danger">
                {err}
              </Alert>
            ) : null}
            {msg ? (
              <Alert title="Статус" tone="success">
                {msg}
              </Alert>
            ) : null}

            <section className="dar-panel dar-stack">
              <div className="dar-row" style={{ justifyContent: 'space-between' }}>
                <strong>Текущая подписка</strong>
                <Badge tone="accent">{sub?.plan_code ?? 'нет'}</Badge>
              </div>
              {sub ? (
                <>
                  <p>
                    Статус: {sub.status}
                    {sub.cancellation_at_period_end ? ' · автопродление выкл.' : ''}
                    {sub.recurring_enabled ? ' · рекуррент вкл.' : ''}
                  </p>
                  <p>
                    Доступ до: <strong>{sub.access_until}</strong>
                    {sub.trial_ends_at ? ` · trial до ${sub.trial_ends_at}` : ''}
                  </p>
                  <p style={{ fontSize: 'var(--dar-text-sm)', color: 'var(--dar-color-text-muted)' }}>
                    Сумма плана (server): {formatRub(sub.amount_minor)} · версия цены {sub.price_version}
                  </p>
                </>
              ) : (
                <p>Подписка ещё не оформлена.</p>
              )}
              <div className="dar-row" style={{ gap: '0.5rem', flexWrap: 'wrap' }}>
                <Button variant="secondary" onClick={() => void cancel()} disabled={!sub}>
                  Отменить автопродление
                </Button>
                <Button variant="secondary" onClick={() => void removePaymentMethod()} disabled={!sub}>
                  Удалить способ оплаты
                </Button>
                <a href="/app/profile">Удаление аккаунта → профиль</a>
              </div>
              <p style={{ fontSize: 'var(--dar-text-sm)', color: 'var(--dar-color-text-muted)' }}>
                Отмена — один поток из профиля/биллинга. Удаление payment method и аккаунта не маскируются.
              </p>
            </section>

            <section className="dar-panel dar-stack">
              <h2 style={{ margin: 0, fontSize: '1.05rem' }}>Тарифы (server price table)</h2>
              <select
                value={selectedPlan}
                onChange={(e) => setSelectedPlan(e.target.value)}
                aria-label="План"
              >
                {plans.map((p) => (
                  <option key={p.plan_code} value={p.plan_code}>
                    {p.label}: {formatRub(p.amount_minor)} / {p.period_days} дн.
                    {p.trial_days ? ` (trial ${p.trial_days}д)` : ''}
                  </option>
                ))}
              </select>
              <Alert title="Отдельное согласие" tone="info">
                Рекуррентные списания — отдельное действие: сумма, период, дата следующего списания, путь отмены.
              </Alert>
              <Checkbox
                id="pay-recurring"
                checked={recurring}
                onChange={setRecurring}
                label="Отдельно соглашаюсь на рекуррентные списания (payment_recurring)"
              />
              {paymentDoc ? (
                <a href={`${getApiBase()}/legal/documents/${paymentDoc.id}/text`} target="_blank" rel="noreferrer">
                  Текст согласия v{paymentDoc.consent_version}
                </a>
              ) : null}
              <div className="dar-row" style={{ gap: '0.5rem', flexWrap: 'wrap' }}>
                <Button onClick={() => void subscribe()}>Оформить план</Button>
                <Button variant="secondary" onClick={() => void enableRecurring()} disabled={!sub}>
                  Включить рекуррент отдельно
                </Button>
              </div>
            </section>

            <section className="dar-panel dar-stack">
              <h2 style={{ margin: 0, fontSize: '1.05rem' }}>История операций</h2>
              {payments.length === 0 ? (
                <p>Пока нет платежей.</p>
              ) : (
                <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                  {payments.map((p) => (
                    <li key={p.id}>
                      {p.created_at}: {formatRub(p.amount_minor)} {p.currency} — {p.status}
                      {p.receipt_ref ? ` · чек ${p.receipt_ref}` : ' · чек не выдан (нет capability/review)'}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        }
      />
    </div>
  );
}

function PRICE_FALLBACK(sub: Subscription): { amount_minor: number; period_days: number } {
  return { amount_minor: sub.amount_minor, period_days: 30 };
}
