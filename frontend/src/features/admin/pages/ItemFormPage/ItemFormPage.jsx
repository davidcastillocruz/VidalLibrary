import { useId, useState } from 'react';
import { useNavigate, useParams } from 'react-router';

import Button from '@/components/Button/Button';
import ConfirmButton from '@/components/ConfirmButton/ConfirmButton';
import Field from '@/components/Field/Field';
import Icon from '@/components/Icon/Icon';
import Notice from '@/components/Notice/Notice';
import Select from '@/components/Select/Select';
import CoverEditor from '@/features/admin/components/CoverEditor/CoverEditor';
import { useAction } from '@/features/admin/hooks/useAction';
import { KINDS } from '@/features/catalog/kinds';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { useRequest } from '@/hooks/useRequest';
import { useSubmit } from '@/hooks/useSubmit';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';
import { useNotify } from '@/notifications/useNotify';
import NotFoundPage from '@/pages/NotFoundPage/NotFoundPage';
import { api } from '@/utils/api';
import shared from '@/features/admin/adminStyles.module.css';

import styles from './ItemFormPageStyle.module.css';
import translations from './ItemFormPageTranslation.json';

// The limits of catalog_schemas.py, checked before sending
const TITLE_MAX_LENGTH = 300;
const CREATOR_MAX_LENGTH = 200;
const SYNOPSIS_MAX_LENGTH = 5000;
const MIN_YEAR = 1450;
const MAX_YEAR = 2100;
const MAX_COPIES = 100;
const MAX_GENRES = 10;
const EMPTY = { kind: 'book', title: '', creator: '', year: '', copies: '1', language_id: '', genre_ids: [], synopsis: '' };

// A work as the form edits it: every field a string, as the inputs give them
function toForm(item) {
  return {
    kind: item.kind,
    title: item.title,
    creator: item.creator,
    year: item.year ? String(item.year) : '',
    copies: String(item.copies),
    language_id: item.language?.id ?? '',
    genre_ids: item.genres.map((genre) => genre.id),
    synopsis: item.synopsis ?? '',
  };
}

// Adding a work (/admin/catalog/new) or editing one (/admin/catalog/:id). The form starts once the work is loaded,
// a new one for each work (key): it keeps what is typed while the work reloads after a save
export default function ItemFormPage() {
  const t = useT(translations);
  const { id } = useParams();
  const item = useRequest(id ? `/catalog/items/${id}` : null);

  if (!id) return <ItemEditor item={null} />;
  if (item.error?.response?.status === 404 || item.error?.response?.status === 422) return <NotFoundPage />;
  // The data kept from another work (going from one to another, or a load that failed) is never edited here: a save
  // would go to that other work
  if (item.error) return <Notice tone="error">{t('loadFailed')}</Notice>;
  if (item.data?.id !== id) return null;
  return <ItemEditor key={item.data.id} item={item.data} reload={item.reload} />;
}

// The fields of a work, its genres, its cover and its deletion. item: null for a new one
function ItemEditor({ item, reload }) {
  const t = useT(translations);
  const kindText = useT(kindTranslations);
  const navigate = useNavigate();
  const notify = useNotify();
  const { language } = useLanguage();
  const synopsisId = useId();
  const { submit, sending, error } = useSubmit();
  const { run, running } = useAction();
  const editing = Boolean(item);
  const id = item?.id;

  const [form, setForm] = useState(() => (item ? toForm(item) : EMPTY));
  const [invalid, setInvalid] = useState({});
  const genres = useRequest('/catalog/genres', { kind: form.kind });
  // Only the genres of the kind chosen: while the ones of a new kind load, the old ones (still in genres.data) can't
  // be pressed into the form, where they would stay without a chip to take them out
  const kindGenres = (genres.data ?? []).filter((genre) => genre.kind === form.kind);
  const languages = useRequest('/catalog/languages');

  function set(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function toggleGenre(genreId) {
    setForm((current) => ({
      ...current,
      genre_ids: current.genre_ids.includes(genreId)
        ? current.genre_ids.filter((other) => other !== genreId)
        : [...current.genre_ids, genreId],
    }));
  }

  async function save(event) {
    event.preventDefault();
    const found = {};
    if (!form.title.trim()) found.title = t('required');
    if (!form.creator.trim()) found.creator = t('required');
    const year = Number(form.year);
    if (form.year && (!Number.isInteger(year) || year < MIN_YEAR || year > MAX_YEAR)) found.year = t('yearInvalid', { min: MIN_YEAR, max: MAX_YEAR });
    const copies = Number(form.copies);
    if (!Number.isInteger(copies) || copies < 1 || copies > MAX_COPIES) found.copies = t('copiesInvalid', { max: MAX_COPIES });
    if (form.genre_ids.length > MAX_GENRES) found.genres = t('tooManyGenres', { max: MAX_GENRES });
    setInvalid(found);
    if (Object.keys(found).length) return;

    const body = {
      kind: form.kind,
      title: form.title,
      creator: form.creator,
      year: form.year ? year : null,
      copies,
      language_id: form.language_id || null,
      genre_ids: form.genre_ids,
      synopsis: form.synopsis,
    };
    const { data } = await submit(() =>
      editing ? api.put(`/admin/catalog/items/${id}`, body) : api.post('/admin/catalog/items', body),
    );
    if (!data) return;
    notify({ tone: 'success', text: data.message, language });
    if (editing) reload();
    else navigate(`/admin/catalog/${data.id}`, { replace: true });
  }

  async function remove() {
    if (await run('delete', () => api.delete(`/admin/catalog/items/${id}`), t('deleteFailed'))) {
      navigate('/admin/catalog', { replace: true });
    }
  }

  return (
    <main className={shared.page}>
      <title>{`${editing ? item.title : t('newTitle')} · Biblioteca Vidal i Barraquer`}</title>
      <div className={shared.heading}>
        <div>
          <Button variant="link" to="/admin/catalog">
            <Icon name="arrowLeft" size={14} />
            {t('back')}
          </Button>
          <h1 className={styles.title}>{editing ? item.title : t('newTitle')}</h1>
        </div>
        {editing && (
          <Button variant="secondary" to={`/items/${id}`}>
            {t('view')}
          </Button>
        )}
      </div>

      <div className={styles.layout}>
        <form className={`${shared.panel} ${styles.form}`} onSubmit={save} noValidate>
          <div className={styles.kinds} role="radiogroup" aria-label={t('kind')}>
            {KINDS.map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={form.kind === option}
                className={shared.chip}
                onClick={() => setForm((current) => ({ ...current, kind: option, genre_ids: [] }))}
              >
                {kindText(option)}
              </button>
            ))}
          </div>
          <Field label={t('titleLabel')} value={form.title} maxLength={TITLE_MAX_LENGTH} error={invalid.title} onChange={(e) => set('title', e.target.value)} />
          <Field
            label={t(`creator_${form.kind}`)}
            value={form.creator}
            maxLength={CREATOR_MAX_LENGTH}
            error={invalid.creator}
            onChange={(e) => set('creator', e.target.value)}
          />
          <div className={styles.pair}>
            <Field label={t('year')} inputMode="numeric" value={form.year} error={invalid.year} onChange={(e) => set('year', e.target.value)} />
            <Field
              label={t('copies')}
              type="number"
              min={1}
              max={MAX_COPIES}
              value={form.copies}
              error={invalid.copies}
              onChange={(e) => set('copies', e.target.value)}
            />
          </div>
          <Select
            label={t('language')}
            value={form.language_id}
            onChange={(e) => set('language_id', e.target.value)}
            options={[
              { value: '', label: t('noLanguage') },
              ...(languages.data ?? []).map((option) => ({ value: option.id, label: option.name })),
            ]}
          />
          <fieldset className={styles.genres}>
            <legend className={styles.legend}>{t('genres')}</legend>
            {genres.data && !genres.loading && kindGenres.length === 0 && <p className={styles.help}>{t('noGenres')}</p>}
            <div className={shared.chips}>
              {kindGenres.map((genre) => (
                <button
                  key={genre.id}
                  type="button"
                  className={shared.chip}
                  aria-pressed={form.genre_ids.includes(genre.id)}
                  onClick={() => toggleGenre(genre.id)}
                >
                  {genre.name}
                </button>
              ))}
            </div>
            {invalid.genres && <p className={styles.error}>{invalid.genres}</p>}
          </fieldset>
          <div className={styles.textareaField}>
            <label htmlFor={synopsisId} className={styles.legend}>
              {t('synopsis')}
            </label>
            <textarea
              id={synopsisId}
              className={styles.textarea}
              rows={6}
              maxLength={SYNOPSIS_MAX_LENGTH}
              value={form.synopsis}
              onChange={(e) => set('synopsis', e.target.value)}
            />
          </div>
          {error && <Notice tone="error">{error.message}</Notice>}
          <div className={styles.submit}>
            <Button type="submit" size="large" loading={sending}>
              {editing ? t('save') : t('create')}
            </Button>
          </div>
        </form>

        <aside className={styles.side}>
          {editing ? (
            <>
              <section className={shared.panel}>
                <h2>{t('cover')}</h2>
                <CoverEditor item={item} onChanged={reload} />
              </section>
              <section className={shared.panel}>
                <h2>{t('danger')}</h2>
                <p className={styles.help}>{t('deleteHelp')}</p>
                <div>
                  <ConfirmButton variant="danger" question={t('deleteQuestion')} loading={running === 'delete'} onConfirm={remove}>
                    <Icon name="trash" size={14} />
                    {t('delete')}
                  </ConfirmButton>
                </div>
              </section>
            </>
          ) : (
            <p className={styles.help}>{t('coverLater')}</p>
          )}
        </aside>
      </div>
    </main>
  );
}
