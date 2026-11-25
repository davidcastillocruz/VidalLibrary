import { Link } from 'react-router';

import Cover from '@/components/Cover/Cover';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { useT } from '@/languages/useT';

import styles from './ItemCardStyle.module.css';
import translations from './ItemCardTranslation.json';

// A work in the grid of the catalog: its cover, title, who made it, and whether a copy is free
export default function ItemCard({ item }) {
  const t = useT(translations);
  const kind = useT(kindTranslations);
  const free = item.available > 0;

  return (
    <Link to={`/items/${item.id}`} className={styles.card}>
      <div className={styles.cover}>
        <Cover item={item} size="small" />
      </div>
      <div className={styles.body}>
        <p className={styles.kind}>
          {kind(item.kind)}
          {item.year && ` · ${item.year}`}
        </p>
        <h3 className={styles.title}>{item.title}</h3>
        <p className={styles.creator}>{item.creator}</p>
        <p className={`${styles.status} ${free ? styles.free : styles.out}`}>
          {free ? t(item.available === 1 ? 'freeOne' : 'free', { count: item.available }) : t('out')}
        </p>
      </div>
    </Link>
  );
}
