import { Link, useLocation } from 'react-router';

import { useT } from '@/languages/useT';

import styles from './NotFoundPageStyle.module.css';
import translations from './NotFoundPageTranslation.json';

// Any route that doesn't exist: says which one and leads back to the start
export default function NotFoundPage() {
  const t = useT(translations);
  const { pathname } = useLocation();

  return (
    <main className={styles.page}>
      <title>{t('pageTitle')}</title>
      <h1 className={styles.title}>{t('title')}</h1>
      <p className={styles.text}>{t('text', { path: pathname })}</p>
      <Link to="/" className={styles.back}>
        {t('back')}
      </Link>
    </main>
  );
}
