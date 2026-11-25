import LanguageSwitch from '@/components/LanguageSwitch/LanguageSwitch';
import ThemeSwitch from '@/components/ThemeSwitch/ThemeSwitch';
import { useT } from '@/languages/useT';

import styles from './SiteFooterStyle.module.css';
import translations from './SiteFooterTranslation.json';

// The bottom of every page, a band of the institute's blue: what the library lends and how, where it is, and the
// language and theme of the page
export default function SiteFooter() {
  const t = useT(translations);

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.about}>
          <p className={styles.name}>{t('name')}</p>
          <p className={styles.rules}>{t('rules')}</p>
        </div>
        <div className={styles.place}>
          <p className={styles.label}>{t('where')}</p>
          <p>Institut F. Vidal i Barraquer</p>
          <p>Av. Lluís Companys · Tarragona</p>
        </div>
        <div className={styles.controls}>
          <LanguageSwitch />
          <ThemeSwitch />
        </div>
      </div>
    </footer>
  );
}
