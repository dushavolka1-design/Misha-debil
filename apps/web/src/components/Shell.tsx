'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import type { ReactNode } from 'react';
import { useEffect, useId, useRef, useState } from 'react';

import { FileSearch, FilePenLine } from 'lucide-react';

import { CompactDisclaimer } from './CompactDisclaimer';
import { DemoModeBanner } from './DemoModeBanner';
import { EnterMotion } from './EnterMotion';
import { ToastProvider } from './Toast';
import { getApiBase } from '../lib/apiBase';

type AppSection = 'analyzer' | 'generator';

function resolveSection(pathname: string): AppSection | null {
  if (
    pathname.startsWith('/app/generator') ||
    pathname.startsWith('/app/forms') ||
    pathname.startsWith('/app/entry-wizard') ||
    pathname.startsWith('/app/sources')
  ) {
    return 'generator';
  }
  if (
    pathname.startsWith('/app/analyzer') ||
    pathname.startsWith('/app/upload') ||
    pathname.startsWith('/app/compare') ||
    pathname.startsWith('/app/jobs') ||
    pathname.startsWith('/app/reports') ||
    pathname === '/app'
  ) {
    return 'analyzer';
  }
  return null;
}

function UserMenu() {
  const menuId = useId();
  const [open, setOpen] = useState(false);
  const [letter, setLetter] = useState('А');
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onEsc);
    };
  }, []);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    void fetch(`${getApiBase()}/auth/me`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(async (me: { display_name?: string; email?: string; has_avatar?: boolean } | null) => {
        if (!me || cancelled) return;
        const name = (me.display_name || me.email || 'А').trim();
        setLetter(name.charAt(0).toUpperCase() || 'А');
        if (!me.has_avatar) return;
        const res = await fetch(`${getApiBase()}/auth/me/avatar`, { credentials: 'include' });
        if (!res.ok || cancelled) return;
        objectUrl = URL.createObjectURL(await res.blob());
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setAvatarUrl(objectUrl);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, []);

  async function logout() {
    await fetch(`${getApiBase()}/auth/logout`, { method: 'POST', credentials: 'include' }).catch(
      () => undefined,
    );
    router.push('/auth/login');
  }

  return (
    <div className="dar-user-menu" ref={wrapRef}>
      <button
        type="button"
        className="dar-user-menu__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="dar-user-menu__avatar" aria-hidden="true">
          {avatarUrl ? <img src={avatarUrl} alt="" /> : letter}
        </span>
        <span className="dar-sr-only">Меню пользователя</span>
      </button>
      {open ? (
        <ul id={menuId} className="dar-user-menu__dropdown" role="menu">
          <li role="none">
            <Link
              href="/app/sources"
              className="dar-user-menu__item"
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              Источники норм
            </Link>
          </li>
          <li role="none">
            <Link
              href="/app/profile"
              className="dar-user-menu__item"
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              Профиль и согласия
            </Link>
          </li>
          <li role="none">
            <Link
              href="/app/billing"
              className="dar-user-menu__item"
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              Подписка
            </Link>
          </li>
          <li role="none">
            <button
              type="button"
              className="dar-user-menu__item"
              role="menuitem"
              onClick={() => void logout()}
            >
              Выйти
            </button>
          </li>
        </ul>
      ) : null}
    </div>
  );
}

function MainNavLink({
  href,
  label,
  active,
  icon,
}: {
  href: string;
  label: string;
  active: boolean;
  icon: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`dar-main-nav__link ${active ? 'dar-main-nav__link--active' : ''}`}
      aria-current={active ? 'page' : undefined}
    >
      {icon}
      {label}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const section = resolveSection(pathname);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <ToastProvider>
      <EnterMotion />
      <div className="dar-app-shell">
        <a className="dar-skip-link" href="#main">
          Перейти к содержимому
        </a>
        <header className={`dar-topbar${scrolled ? ' dar-topbar--scrolled' : ''}`}>
          <div className="dar-topbar__inner dar-topbar__inner--app">
            <Link href="/app/analyzer" className="dar-brand-lockup" aria-label="Docly — кабинет">
              <img
                src="/docly-logo.png"
                alt=""
                className="dar-brand-mark"
                width={40}
                height={40}
                aria-hidden="true"
              />
              <span className="dar-brand-text">Docly</span>
            </Link>

            <nav className="dar-main-nav" aria-label="Основные разделы">
              <MainNavLink
                href="/app/analyzer"
                label="Анализатор"
                active={section === 'analyzer'}
                icon={<FileSearch size={18} aria-hidden="true" />}
              />
              <MainNavLink
                href="/app/generator"
                label="Генерация"
                active={section === 'generator'}
                icon={<FilePenLine size={18} aria-hidden="true" />}
              />
            </nav>

            <UserMenu />
          </div>
        </header>

        <div className="dar-app-body">
          <div className="dar-main-wrap">
            <main id="main" className="dar-main dar-main--wide" tabIndex={-1}>
              <DemoModeBanner />
              {children}
              <CompactDisclaimer />
            </main>
          </div>
        </div>

        <nav className="dar-mobile-nav" aria-label="Мобильная навигация">
          <Link href="/app/analyzer" aria-current={section === 'analyzer' ? 'page' : undefined}>
            Анализатор
          </Link>
          <Link href="/app/generator" aria-current={section === 'generator' ? 'page' : undefined}>
            Генерация
          </Link>
        </nav>
      </div>
    </ToastProvider>
  );
}

export function MarketingShell({ children }: { children: ReactNode }) {
  return (
    <div className="dar-marketing">
      <EnterMotion />
      <a className="dar-skip-link" href="#main">
        Перейти к содержимому
      </a>
      <header className="dar-marketing-header">
        <div className="dar-content dar-marketing-header__inner">
          <Link href="/" className="dar-brand-lockup" aria-label="Docly">
            <img
              src="/docly-logo.png"
              alt=""
              className="dar-brand-mark"
              width={40}
              height={40}
              aria-hidden="true"
            />
            <span className="dar-brand-text">Docly</span>
          </Link>
          <div className="dar-row">
            <Link href="/auth/login" className="dar-topbar__link">
              Вход
            </Link>
            <Link href="/auth/register" className="dar-btn dar-btn--primary">
              Создать аккаунт
            </Link>
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
