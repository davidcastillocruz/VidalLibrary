import Notice from '@/components/Notice/Notice';
import NameList from '@/features/admin/components/NameList/NameList';
import { KIND_PLURALS, KINDS } from '@/features/catalog/kinds';
import kindTranslations from '@/features/catalog/kindsTranslation.json';
import { useRequest } from '@/hooks/useRequest';
import { useT } from '@/languages/useT';
import { api } from '@/utils/api';
import shared from '@/features/admin/adminStyles.module.css';

import styles from './ListsPageStyle.module.css';
import translations from './ListsPageTranslation.json';

// The lists the catalog is filtered by: the genres of each kind, and the languages shared by every work
export default function ListsPage() {
  const t = useT(translations);
  const kindText = useT(kindTranslations);
  const genres = useRequest('/catalog/genres');
  const languages = useRequest('/catalog/languages');

  return (
    <main className={shared.page}>
      <title>{`${t('title')} · Biblioteca Vidal i Barraquer`}</title>
      <div className={shared.heading}>
        <div>
          <h1>{t('title')}</h1>
          <p className={shared.lead}>{t('lead')}</p>
        </div>
      </div>

      {(genres.error || languages.error) && <Notice tone="error">{t('failed')}</Notice>}

      {genres.data && languages.data && (
        <div className={styles.grid}>
          {KINDS.map((kind) => (
            <NameList
              key={kind}
              title={t('genresOf', { kind: kindText(KIND_PLURALS[kind]).toLowerCase() })}
              entries={genres.data.filter((genre) => genre.kind === kind)}
              deleteQuestion={t('deleteGenre')}
              onCreate={(name) => api.post('/admin/catalog/genres', { kind, name })}
              onRename={(genre, name) => api.put(`/admin/catalog/genres/${genre.id}`, { name })}
              onDelete={(genre) => api.delete(`/admin/catalog/genres/${genre.id}`)}
              onChanged={genres.reload}
            />
          ))}
          <NameList
            title={t('languages')}
            entries={languages.data}
            deleteQuestion={t('deleteLanguage')}
            onCreate={(name) => api.post('/admin/catalog/languages', { name })}
            onRename={(language, name) => api.put(`/admin/catalog/languages/${language.id}`, { name })}
            onDelete={(language) => api.delete(`/admin/catalog/languages/${language.id}`)}
            onChanged={languages.reload}
          />
        </div>
      )}
    </main>
  );
}
