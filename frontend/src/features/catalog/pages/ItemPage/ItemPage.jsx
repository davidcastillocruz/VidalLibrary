import { useState } from 'react';
import { Link, useLocation, useParams } from 'react-router';

import Button from '@/components/Button/Button';
import Cover from '@/components/Cover/Cover';
import Icon from '@/components/Icon/Icon';
import Notice from '@/components/Notice/Notice';
import Skeleton from '@/components/Skeleton/Skeleton';
import { useCurrentUser } from '@/features/auth/currentUser/useCurrentUser';
import { KIND_ICONS } from '@/features/catalog/kinds';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { useRequest } from '@/hooks/useRequest';
import { useSubmit } from '@/hooks/useSubmit';
import { useT } from '@/languages/useT';
import NotFoundPage from '@/pages/NotFoundPage/NotFoundPage';
import { api } from '@/utils/api';

import styles from './ItemPageStyle.module.css';
import translations from './ItemPageTranslation.json';

// Who made a work, by its kind: a book has an author, a film a director, a board game a designer
const CREATOR_LABELS = { book: 'author', film: 'director', board_game: 'designer' };

// A work on its own page: everything about it and how many copies are free, with the button to reserve one
export default function ItemPage() {
  const t = useT(translations);
  const kindText = useT(kindTranslations);
  const { id } = useParams();
  const location = useLocation();
  const { user } = useCurrentUser();
  const { data: item, error, reload } = useRequest(`/catalog/items/${id}`);
  const { submit, sending, error: reserveError } = useSubmit();
  const [reserved, setReserved] = useState(null);

  if (error?.response?.status === 404 || error?.response?.status === 422) return <NotFoundPage />;
  if (error) return <Notice tone="error">{t('failed')}</Notice>;
  if (!item) {
    return (
      <main className={styles.page} aria-busy="true" aria-label={t('loading')}>
        <div className={styles.layout}>
          <div className={styles.cover}>
            <Skeleton shape="cover" />
          </div>
          <div className={styles.details}>
            <Skeleton width="20%" />
            <Skeleton shape="title" />
            <Skeleton width="35%" />
            <Skeleton width="100%" />
            <Skeleton width="100%" />
            <Skeleton width="80%" />
          </div>
        </div>
      </main>
    );
  }

  async function reserve() {
    setReserved(null);
    const { data } = await submit(() => api.post('/loans', { item_id: item.id }));
    if (data) setReserved(data.message);
    reload();
  }

  const free = item.available > 0;

  return (
    <main className={styles.page}>
      <title>{`${item.title} · Biblioteca Vidal i Barraquer`}</title>
      <Link to="/" className={styles.back}>
        <Icon name="arrowLeft" size={16} />
        {t('back')}
      </Link>

      <div className={styles.layout}>
        <div className={styles.cover}>
          <Cover item={item} size="large" />
        </div>

        <article className={styles.details}>
          <p className={styles.kind}>
            <Icon name={KIND_ICONS[item.kind]} size={16} />
            {kindText(item.kind)}
          </p>
          <h1 className={styles.title}>{item.title}</h1>
          <p className={styles.creator}>
            <span className="sr-only">{t(CREATOR_LABELS[item.kind])}: </span>
            {item.creator}
          </p>

          <dl className={styles.facts}>
            {item.year && (
              <div>
                <dt>{t('year')}</dt>
                <dd>{item.year}</dd>
              </div>
            )}
            {item.language && (
              <div>
                <dt>{t('language')}</dt>
                <dd>{item.language.name}</dd>
              </div>
            )}
            <div>
              <dt>{t('copies')}</dt>
              <dd>{t('copiesFree', { free: item.available, copies: item.copies })}</dd>
            </div>
          </dl>

          {item.genres.length > 0 && (
            <ul className={styles.genres} aria-label={t('genres')}>
              {item.genres.map((genre) => (
                <li key={genre.id}>
                  <Link to={`/?kind=${item.kind}&genre=${genre.id}`}>{genre.name}</Link>
                </li>
              ))}
            </ul>
          )}

          {item.synopsis && <p className={styles.synopsis}>{item.synopsis}</p>}

          <section className={styles.reserve} aria-label={t('reserveSection')}>
            <p className={`${styles.availability} ${free ? styles.free : ''}`}>
              {free ? t('available') : t('unavailable')}
            </p>
            {user === null && (
              <Button size="large" to="/login" state={{ from: location.pathname }}>
                {t('signInToReserve')}
              </Button>
            )}
            {user && (
              <Button size="large" onClick={reserve} loading={sending} disabled={!free}>
                {t('reserve')}
              </Button>
            )}
            {user && <p className={styles.hint}>{t('hint')}</p>}
            {reserved && (
              <Notice tone="success" title={reserved}>
                <Link to="/loans">{t('seeLoans')}</Link>
              </Notice>
            )}
            {reserveError && <Notice tone="error">{reserveError.message}</Notice>}
          </section>

          {user?.role === 'librarian' && (
            <Button variant="link" to={`/admin/catalog/${item.id}`}>
              <Icon name="pencil" size={14} />
              {t('edit')}
            </Button>
          )}
        </article>
      </div>
    </main>
  );
}
