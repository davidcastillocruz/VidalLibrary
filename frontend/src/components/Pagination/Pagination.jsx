import Button from '@/components/Button/Button';
import Icon from '@/components/Icon/Icon';
import { useT } from '@/languages/useT';

import styles from './PaginationStyle.module.css';
import translations from './PaginationTranslation.json';

// Previous and next under a list, with where the reader is. Nothing when everything fits in one page. A new page
// starts at the top of the screen: from down here it would begin out of sight
export default function Pagination({ page, pageSize, total, onChange }) {
  const t = useT(translations);
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages === 1) return null;

  function go(next) {
    onChange(next);
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: still ? 'auto' : 'smooth' });
  }

  return (
    <nav className={styles.pagination} aria-label={t('label')}>
      <Button variant="secondary" disabled={page <= 1} onClick={() => go(page - 1)}>
        <Icon name="arrowLeft" size={16} />
        {t('previous')}
      </Button>
      <span className={styles.where}>{t('where', { page, pages })}</span>
      <Button variant="secondary" disabled={page >= pages} onClick={() => go(page + 1)}>
        {t('next')}
        <Icon name="arrowLeft" size={16} className={styles.flip} />
      </Button>
    </nav>
  );
}
