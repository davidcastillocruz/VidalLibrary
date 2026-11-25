import Icon from '@/components/Icon/Icon';
import Notice from '@/components/Notice/Notice';
import Pagination from '@/components/Pagination/Pagination';
import Select from '@/components/Select/Select';
import Skeleton from '@/components/Skeleton/Skeleton';
import ItemCard from '@/features/catalog/components/ItemCard/ItemCard';
import { KIND_ICONS, KIND_PLURALS, KINDS, PAGE_SIZE } from '@/features/catalog/kinds';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { SEARCH_MAX_LENGTH, useLastPage, useListParams } from '@/hooks/useListParams';
import { useRequest } from '@/hooks/useRequest';
import { useT } from '@/languages/useT';

import styles from './CatalogPageStyle.module.css';
import translations from './CatalogPageTranslation.json';

// Covers drawn while the first page loads: two rows of a wide screen, like the page that comes
const LOADING_CARDS = 12;

// The catalog: every work of the library, by kind, searched and filtered. Everything chosen lives in the address
// (?kind=film&q=pa&page=2), so a search can be shared or come back to with the back button
export default function CatalogPage() {
  const t = useT(translations);
  const kindText = useT(kindTranslations);
  const { params, change, search, setSearch } = useListParams();
  const kind = params.get('kind') ?? '';
  const q = params.get('q') ?? '';
  const genre = params.get('genre') ?? '';
  const language = params.get('language') ?? '';
  const sort = params.get('sort') ?? 'title';
  const page = Number(params.get('page')) || 1;

  const query = { kind, q, genre, language, sort, page };
  const items = useRequest('/catalog/items', query);
  useLastPage(page, items.data?.total, PAGE_SIZE, change);
  const genres = useRequest('/catalog/genres', { kind });
  const languages = useRequest('/catalog/languages');

  const total = items.data?.total ?? 0;
  const filtered = Boolean(q || genre || language);

  return (
    <main className={styles.page}>
      <title>{t('pageTitle')}</title>
      <header className={styles.intro}>
        <h1 className={styles.title}>{t('title')}</h1>
        <p className={styles.lead}>{t('lead')}</p>
      </header>

      <div className={styles.tabs} role="tablist" aria-label={t('kinds')}>
        {['', ...KINDS].map((option) => (
          <button
            key={option || 'all'}
            type="button"
            role="tab"
            aria-selected={kind === option}
            className={styles.tab}
            onClick={() => change({ kind: option, genre: '' })}
          >
            {option && <Icon name={KIND_ICONS[option]} size={18} />}
            {option ? kindText(KIND_PLURALS[option]) : t('all')}
          </button>
        ))}
      </div>

      <div className={styles.filters}>
        <label className={styles.search}>
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
        <Select
          label={t('genre')}
          value={genre}
          onChange={(event) => change({ genre: event.target.value })}
          options={[
            { value: '', label: t('anyGenre') },
            ...(genres.data ?? []).map((option) => ({
              value: option.id,
              label: kind ? option.name : `${option.name} · ${kindText(option.kind)}`,
            })),
          ]}
        />
        <Select
          label={t('language')}
          value={language}
          onChange={(event) => change({ language: event.target.value })}
          options={[
            { value: '', label: t('anyLanguage') },
            ...(languages.data ?? []).map((option) => ({ value: option.id, label: option.name })),
          ]}
        />
        <Select
          label={t('sort')}
          value={sort}
          onChange={(event) => change({ sort: event.target.value === 'title' ? '' : event.target.value })}
          options={[
            { value: 'title', label: t('byTitle') },
            { value: 'newest', label: t('byNewest') },
            { value: 'year', label: t('byYear') },
          ]}
        />
      </div>

      {items.error && <Notice tone="error">{t('failed')}</Notice>}

      {!items.data && !items.error && (
        <ul className={styles.grid} aria-busy="true" aria-label={t('loading')}>
          {Array.from({ length: LOADING_CARDS }, (_, index) => (
            <li key={index} className={styles.loadingCard}>
              <Skeleton shape="cover" />
              <Skeleton width="45%" />
              <Skeleton shape="title" />
              <Skeleton width="60%" />
            </li>
          ))}
        </ul>
      )}

      {items.data && (
        <>
          <p className={styles.count} aria-live="polite">
            {t(total === 1 ? 'countOne' : 'count', { count: total })}
          </p>
          {items.data.items.length > 0 ? (
            <ul className={styles.grid} aria-busy={items.loading || undefined}>
              {items.data.items.map((item) => (
                <li key={item.id}>
                  <ItemCard item={item} />
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.empty}>
              <h2>{t('emptyTitle')}</h2>
              <p>{filtered ? t('emptyFiltered') : t('empty')}</p>
            </div>
          )}
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={(next) => change({ page: next })} />
        </>
      )}
    </main>
  );
}
