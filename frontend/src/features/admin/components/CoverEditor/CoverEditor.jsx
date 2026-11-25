import { useRef } from 'react';

import Button from '@/components/Button/Button';
import ConfirmButton from '@/components/ConfirmButton/ConfirmButton';
import Cover from '@/components/Cover/Cover';
import Icon from '@/components/Icon/Icon';
import { useAction } from '@/features/admin/hooks/useAction';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';
import { useNotify } from '@/notifications/useNotify';
import { api } from '@/utils/api';

import styles from './CoverEditorStyle.module.css';
import translations from './CoverEditorTranslation.json';

// Biggest cover the backend takes: MAX_BYTES of cover_image.py. Checked here too, so a huge photo isn't sent for nothing
const MAX_BYTES = 5 * 1024 * 1024;

// The cover of a work being edited: a new one from a file, or none (then the drawn one shows). onChanged() after
// either, so the page reads the new version of the cover
export default function CoverEditor({ item, onChanged }) {
  const t = useT(translations);
  const { language } = useLanguage();
  const notify = useNotify();
  const input = useRef(null);
  const { run, running } = useAction();

  async function upload(file) {
    if (!file) return;
    if (file.size > MAX_BYTES || !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      notify({ tone: 'error', title: t('failed'), text: t('invalid'), language });
      return;
    }
    const form = new FormData();
    form.append('cover', file);
    // A big photo can take longer than the usual 10 s on a slow connection
    const done = await run('upload', () => api.put(`/admin/catalog/items/${item.id}/cover`, form, { timeout: 60_000 }), t('failed'));
    if (done) onChanged();
  }

  async function remove() {
    if (await run('remove', () => api.delete(`/admin/catalog/items/${item.id}/cover`), t('removeFailed'))) onChanged();
  }

  return (
    <div className={styles.editor}>
      <div className={styles.preview}>
        <Cover item={item} />
      </div>
      <input
        ref={input}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => {
          upload(event.target.files[0]);
          event.target.value = '';
        }}
      />
      <div className={styles.actions}>
        <Button variant="secondary" loading={running === 'upload'} onClick={() => input.current.click()}>
          <Icon name="image" size={16} />
          {item.cover ? t('change') : t('add')}
        </Button>
        {item.cover && (
          <ConfirmButton variant="ghost" question={t('removeQuestion')} loading={running === 'remove'} onConfirm={remove}>
            {t('remove')}
          </ConfirmButton>
        )}
      </div>
      <p className={styles.help}>{t('help')}</p>
    </div>
  );
}
