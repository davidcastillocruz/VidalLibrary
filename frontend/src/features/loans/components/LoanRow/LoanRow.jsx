import { Link } from 'react-router';

import Cover from '@/components/Cover/Cover';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';
import { formatDay, libraryDay } from '@/utils/dates';

import styles from './LoanRowStyle.module.css';
import translations from './LoanRowTranslation.json';

// What to say of a loan by its status, and its color
function statusOf(loan, today) {
  if (loan.status === 'requested') return { key: 'pickUntil', day: loan.pickup_until, tone: 'info' };
  if (loan.status === 'active' && loan.due_on < today) return { key: 'overdue', day: loan.due_on, tone: 'danger' };
  if (loan.status === 'active') return { key: 'dueOn', day: loan.due_on, tone: 'success' };
  if (loan.status === 'returned') return { key: 'returned', day: loan.returned_at, tone: 'muted' };
  return { key: 'cancelled', day: loan.cancelled_at, tone: 'muted' };
}

// A loan in a list: the cover and title of its work, what is due and when. children: the actions (cancel, return...)
// and details: anything above the status (the reader, for the desk)
export default function LoanRow({ loan, details, children }) {
  const t = useT(translations);
  const kind = useT(kindTranslations);
  const { language } = useLanguage();
  const status = statusOf(loan, libraryDay());

  return (
    <li className={styles.row}>
      <Link to={`/items/${loan.item.id}`} className={styles.cover} tabIndex={-1} aria-hidden="true">
        <Cover item={loan.item} size="tiny" />
      </Link>
      <div className={styles.body}>
        <p className={styles.kind}>{kind(loan.item.kind)}</p>
        <Link to={`/items/${loan.item.id}`} className={styles.title}>
          {loan.item.title}
        </Link>
        <p className={styles.creator}>{loan.item.creator}</p>
        {details}
        <p className={`${styles.status} ${styles[status.tone]}`}>
          {t(status.key, { day: status.day ? formatDay(status.day, language) : '' })}
        </p>
      </div>
      {children && <div className={styles.actions}>{children}</div>}
    </li>
  );
}
