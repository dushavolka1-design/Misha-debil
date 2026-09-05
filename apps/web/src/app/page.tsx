import Link from 'next/link';
import { FileSearch, FilePenLine, ShieldCheck, LockKeyhole, ScrollText, CheckCircle2 } from 'lucide-react';

import { CompactDisclaimer } from '../components/CompactDisclaimer';
import { DocumentProcessIllustration } from '../components/DocumentProcessIllustration';
import { MarketingShell } from '../components/Shell';

export default function LandingPage() {
  return (
    <MarketingShell>
      <div className="dar-landing">
        <section className="dar-landing-hero" aria-labelledby="hero-title">
          <div className="dar-content dar-landing-hero__grid">
            <div className="dar-landing-hero__copy">
              <p className="dar-landing-eyebrow">Частный продукт · не государственная услуга</p>
              <h1 id="hero-title" className="dar-landing-hero__title">
                Документы — по фактам из файла
              </h1>
              <p className="dar-landing-hero__lead">
                Разберите договор или соберите шаблон без имитации портала госуслуг: факты, риски и поля
                с опорой на файл и реестр источников.
              </p>
              <div className="dar-row dar-landing-hero__cta">
                <Link href="/auth/register" className="dar-btn dar-btn--primary dar-btn--lg">
                  Создать аккаунт
                </Link>
                <Link href="/auth/login" className="dar-btn dar-btn--secondary dar-btn--lg">
                  Войти
                </Link>
              </div>
            </div>
            <DocumentProcessIllustration />
          </div>
        </section>

        <div className="dar-trust" aria-label="Доверие">
          <div className="dar-content dar-trust__inner">
            <div className="dar-trust__item">
              <LockKeyhole size={20} aria-hidden="true" />
              Файлы остаются в вашем контуре
            </div>
            <div className="dar-trust__item">
              <ScrollText size={20} aria-hidden="true" />
              Нормы только из проверенного реестра
            </div>
            <div className="dar-trust__item">
              <ShieldCheck size={20} aria-hidden="true" />
              Без гербов и имитации госуслуг
            </div>
          </div>
        </div>

        <section className="dar-content dar-landing-section" aria-label="Два направления продукта">
          <div className="dar-landing-cards">
            <Link href="/auth/register?intent=analyze" className="dar-product-card">
              <span className="dar-product-card__icon" aria-hidden="true">
                <FileSearch size={22} />
              </span>
              <strong className="dar-product-card__title">Проанализировать документ</strong>
              <span className="dar-product-card__text">
                Факты, риски и пробелы данных со ссылками на фрагменты в файле.
              </span>
              <ul className="dar-product-card__benefits">
                <li>Подсветка цитат в тексте</li>
                <li>Приоритет рисков</li>
                <li>Без юридических гарантий</li>
              </ul>
              <span className="dar-product-card__action">Начать анализ</span>
            </Link>
            <Link href="/auth/register?intent=create" className="dar-product-card">
              <span className="dar-product-card__icon" aria-hidden="true">
                <FilePenLine size={22} />
              </span>
              <strong className="dar-product-card__title">Создать документ</strong>
              <span className="dar-product-card__text">
                Шаблоны и мастер заполнения только после проверки официальных источников.
              </span>
              <ul className="dar-product-card__benefits">
                <li>Понятный статус формы</li>
                <li>Чеклист, если бланка ещё нет</li>
                <li>Памятки сервиса отдельно от гособланков</li>
              </ul>
              <span className="dar-product-card__action">Перейти к шаблонам</span>
            </Link>
          </div>
        </section>

        <section className="dar-content dar-landing-section" aria-labelledby="how-title">
          <h2 id="how-title" className="dar-landing-section__title">
            Как это работает
          </h2>
          <ol className="dar-steps">
            <li className="dar-step-card">
              <span className="dar-step__num" aria-hidden="true">
                1
              </span>
              <div>
                <strong>Загрузите файл или выберите шаблон</strong>
                <p>Документ уходит в защищённую обработку; шаблоны публикуются после проверки источника.</p>
              </div>
            </li>
            <li className="dar-step-card">
              <span className="dar-step__num" aria-hidden="true">
                2
              </span>
              <div>
                <strong>Получите структурированный результат</strong>
                <p>Анализ показывает факты с уверенностью извлечения; генерация собирает поля без выдуманных норм.</p>
              </div>
            </li>
            <li className="dar-step-card">
              <span className="dar-step__num" aria-hidden="true">
                3
              </span>
              <div>
                <strong>Проверьте и решите со специалистом</strong>
                <p>Сервис не заменяет юриста или врача — вы видите пробелы и готовитесь к консультации.</p>
              </div>
            </li>
          </ol>
        </section>

        <section className="dar-content dar-landing-section" aria-labelledby="security-title">
          <div className="dar-panel dar-security-block">
            <h2 id="security-title" className="dar-landing-section__title">
              Безопасность и источники
            </h2>
            <div className="dar-security-badges">
              <article className="dar-security-badge">
                <strong>
                  <LockKeyhole size={18} aria-hidden="true" /> Согласия до файла
                </strong>
                <p>Доступ к загрузке — после проверки согласий; медицинские данные — отдельное согласие.</p>
              </article>
              <article className="dar-security-badge">
                <strong>
                  <ScrollText size={18} aria-hidden="true" /> Реестр, не «память модели»
                </strong>
                <p>Нормы и формы берутся только из реестра с подтверждёнными снимками.</p>
              </article>
              <article className="dar-security-badge">
                <strong>
                  <CheckCircle2 size={18} aria-hidden="true" /> Статус на карточке
                </strong>
                <p>Шаблон без проверки недоступен для заполнения и помечен как требующий проверки источника.</p>
              </article>
              <article className="dar-security-badge">
                <strong>
                  <ShieldCheck size={18} aria-hidden="true" /> Не госуслуги
                </strong>
                <p>Нет гербов, флагов и визуального копирования государственного портала.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="dar-content dar-landing-section" aria-labelledby="cta-title">
          <div className="dar-landing-cta-block dar-landing-cta">
            <h2 id="cta-title" className="dar-landing-section__title">
              Готовы попробовать?
            </h2>
            <p className="dar-landing-cta-block__lead">
              Регистрация открывает анализатор и генерацию в одном кабинете.
            </p>
            <Link href="/auth/register" className="dar-btn dar-btn--primary dar-btn--lg">
              Зарегистрироваться
            </Link>
          </div>
        </section>

        <div className="dar-content dar-landing-disclaimer">
          <CompactDisclaimer />
        </div>
      </div>
    </MarketingShell>
  );
}
