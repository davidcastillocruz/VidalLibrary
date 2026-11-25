import { Outlet } from 'react-router';

import SiteFooter from '@/components/SiteFooter/SiteFooter';
import SiteHeader from '@/components/SiteHeader/SiteHeader';
import { useT } from '@/languages/useT';

import styles from './AppLayoutStyle.module.css';
import translations from './AppLayoutTranslation.json';

// Every page of the app between the header and the footer. The first Tab reaches a link that skips the header, shown
// only while it has the focus
export default function AppLayout() {
  const t = useT(translations);

  return (
    <div className={styles.app}>
      <a href="#content" className={styles.skip}>
        {t('skip')}
      </a>
      <SiteHeader />
      <div id="content" className={styles.content} tabIndex={-1}>
        <Outlet />
      </div>
      <SiteFooter />
    </div>
  );
}
