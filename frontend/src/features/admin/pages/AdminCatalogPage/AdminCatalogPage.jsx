import { Link } from 'react-router';

import Button from '@/components/Button/Button';
import Cover from '@/components/Cover/Cover';
import Icon from '@/components/Icon/Icon';
import Notice from '@/components/Notice/Notice';
import Pagination from '@/components/Pagination/Pagination';
import { KIND_PLURALS, KINDS, PAGE_SIZE } from '@/features/catalog/kinds';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { SEARCH_MAX_LENGTH, useLastPage, useListParams } from '@/hooks/useListParams';
import { useRequest } from '@/hooks/useRequest';
import { useT } from '@/languages/useT';
import shared from '@/features/admin/adminStyles.module.css';

import styles from './AdminCatalogPageStyle.module.css';
import translations from './AdminCatalogPageTranslation.json';

// The catalog to manage: every work with its copies, newest first, and the way to add one
export default function AdminCatalogPage() {
  const t = useT(translations);
  const kindText = useT(kindTranslations);
  const { params, change, search, setSearch } = useListParams();
  const kind = params.get('kind') ?? '';
  const q = params.get('q') ?? '';
  const page = Number(params.get('page')) || 1;

  const { data, error } = useRequest('/catalog/items', { sort: 'newest', kind, q, page });
  useLastPage(page, data?.total, PAGE_SIZE, change);

  return (
    <main className={shared.page}>
      <title>{`${t('title')} · Biblioteca Vidal i Barraquer`}</title>
      <div className={shared.heading}>
        <div>
          <h1>{t('title')}</h1>
          <p className={shared.lead}>{t('lead')}</p>
        </div>
        <Button to="/admin/catalog/new">
          <Icon name="plus" size={16} />
          {t('add')}
        </Button>
      </div>

      <div className={shared.toolbar}>
        <label className={shared.search}>
          <Icon name="search" size={18} />
          <span className="sr-only">{t('search')}</span>
          <input
            type="search"
            value={search}
            maxLength={SEARCH_MAX_LENGTH}
            placeholder={t('searchPlaceholder')}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <div className={shared.chips} role="group" aria-label={t('kind')}>
          {['', ...KINDS].map((option) => (
            <button
              key={option || 'all'}
              type="button"
              className={shared.chip}
              aria-pressed={kind === option}
              onClick={() => change({ kind: option })}
            >
              {option ? kindText(KIND_PLURALS[option]) : t('all')}
            </button>
          ))}
        </div>
      </div>

      {error && <Notice tone="error">{t('failed')}</Notice>}

      {data && (
        <>
          {data.items.length === 0 ? (
            <p className={shared.empty}>{t('empty')}</p>
          ) : (
            <ul className={shared.list}>
              {data.items.map((item) => (
                <li key={item.id} className={styles.row}>
                  <div className={styles.cover}>
                    <Cover item={item} size="tiny" />
                  </div>
                  <div className={styles.body}>
                    <Link to={`/admin/catalog/${item.id}`} className={styles.title}>
                      {item.title}
                    </Link>
                    <p className={styles.meta}>
                      {kindText(item.kind)} · {item.creator}
                      {item.year && ` · ${item.year}`}
                    </p>
                  </div>
                  <p className={styles.copies}>{t('copies', { free: item.available, copies: item.copies })}</p>
                  <Button variant="secondary" to={`/admin/catalog/${item.id}`}>
                    <Icon name="pencil" size={14} />
                    {t('edit')}
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(next) => change({ page: next })} />
        </>
      )}
    </main>
  );
}
