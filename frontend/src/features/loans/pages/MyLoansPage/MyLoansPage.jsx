import { useState } from 'react';

import Button from '@/components/Button/Button';
import Notice from '@/components/Notice/Notice';
import Skeleton from '@/components/Skeleton/Skeleton';
import LoanRow from '@/features/loans/components/LoanRow/LoanRow';
import { useFocusAfterReload } from '@/hooks/useFocusAfterReload';
import { useRequest } from '@/hooks/useRequest';
import { requestError, useNoticeText } from '@/hooks/useSubmit';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';
import { useNotify } from '@/notifications/useNotify';
import { api } from '@/utils/api';

import styles from './MyLoansPageStyle.module.css';
import translations from './MyLoansPageTranslation.json';

// Loans a reader can have open at once: MAX_OPEN_LOANS of loan_rules.py
const MAX_OPEN_LOANS = 3;

// The loans of the reader: what waits at the desk, what it has at home, and what it read before
export default function MyLoansPage() {
  const t = useT(translations);
  const { language } = useLanguage();
  const notify = useNotify();
  const noticeText = useNoticeText();
  const { data: loans, error, reload } = useRequest('/loans');
  const [cancelling, setCancelling] = useState(null);
  // A cancelled reservation moves to the history and its button goes away: the focus goes back to the title
  const { target: title, expect } = useFocusAfterReload(loans);

  async function cancel(loan) {
    setCancelling(loan.id);
    try {
      const { data } = await api.delete(`/loans/${loan.id}`);
      notify({ tone: 'success', text: data.message, language });
    } catch (failure) {
      notify({ tone: 'error', title: t('cancelFailed'), text: noticeText(requestError(failure, language)), language });
    }
    setCancelling(null);
    expect();
    reload();
  }

  const requested = loans?.filter((loan) => loan.status === 'requested') ?? [];
  const active = loans?.filter((loan) => loan.status === 'active') ?? [];
  const history = loans?.filter((loan) => loan.status === 'returned' || loan.status === 'cancelled') ?? [];
  const open = requested.length + active.length;

  return (
    <main className={styles.page}>
      <title>{`${t('title')} · Biblioteca Vidal i Barraquer`}</title>
      <header className={styles.header}>
        <h1 ref={title} tabIndex={-1}>
          {t('title')}
        </h1>
        {loans && <p className={styles.quota}>{t('quota', { open, max: MAX_OPEN_LOANS })}</p>}
      </header>

      {error && <Notice tone="error">{t('failed')}</Notice>}

      {!loans && !error && (
        <ul className={styles.list} aria-busy="true" aria-label={t('loading')}>
          {[0, 1, 2].map((row) => (
            <li key={row} className={styles.loadingRow}>
              <Skeleton shape="cover" />
              <span className={styles.loadingText}>
                <Skeleton width="25%" />
                <Skeleton shape="title" />
                <Skeleton width="40%" />
              </span>
            </li>
          ))}
        </ul>
      )}

      {loans && loans.length === 0 && (
        <div className={styles.empty}>
          <h2>{t('emptyTitle')}</h2>
          <p>{t('empty')}</p>
          <Button to="/">{t('browse')}</Button>
        </div>
      )}

      {requested.length > 0 && (
        <section className={styles.section}>
          <h2>{t('requested')}</h2>
          <p className={styles.note}>{t('requestedNote')}</p>
          <ul className={styles.list}>
            {requested.map((loan) => (
              <LoanRow key={loan.id} loan={loan}>
                <Button variant="secondary" loading={cancelling === loan.id} onClick={() => cancel(loan)}>
                  {t('cancel')}
                </Button>
              </LoanRow>
            ))}
          </ul>
        </section>
      )}

      {active.length > 0 && (
        <section className={styles.section}>
          <h2>{t('active')}</h2>
          <ul className={styles.list}>
            {active.map((loan) => (
              <LoanRow key={loan.id} loan={loan} />
            ))}
          </ul>
        </section>
      )}

      {history.length > 0 && (
        <section className={styles.section}>
          <h2>{t('history')}</h2>
          <ul className={styles.list}>
            {history.map((loan) => (
              <LoanRow key={loan.id} loan={loan} />
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
