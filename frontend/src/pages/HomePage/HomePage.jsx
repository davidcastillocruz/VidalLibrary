import { useT } from '@/languages/useT';

import styles from './HomePageStyle.module.css';
import translations from './HomePageTranslation.json';

// The start of the library, until the catalog takes its place
export default function HomePage() {
  const t = useT(translations);

  return (
    <main className={styles.page}>
      <title>{t('pageTitle')}</title>
      <h1 className={styles.title}>{t('title')}</h1>
    </main>
  );
}
