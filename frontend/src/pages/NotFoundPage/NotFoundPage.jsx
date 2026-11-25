import { useLocation } from 'react-router';

import Button from '@/components/Button/Button';
import { useT } from '@/languages/useT';

import styles from './NotFoundPageStyle.module.css';
import translations from './NotFoundPageTranslation.json';

// Any route that doesn't exist, or a page the user can't see: says which one and leads back to the catalog.
// The shelf mark is the one a misplaced book would have: 404 on no shelf
export default function NotFoundPage() {
  const t = useT(translations);
  const { pathname } = useLocation();

  return (
    <main className={styles.page}>
      <title>{t('pageTitle')}</title>
      <p className={styles.mark} aria-hidden="true">
        404
      </p>
      <h1 className={styles.title}>{t('title')}</h1>
      <p className={styles.text}>{t('text', { path: pathname })}</p>
      <Button to="/">{t('back')}</Button>
    </main>
  );
}
