import { useEffect, useRef, useState } from 'react';

import Button from '@/components/Button/Button';
import ConfirmButton from '@/components/ConfirmButton/ConfirmButton';
import Icon from '@/components/Icon/Icon';
import { useAction } from '@/features/admin/hooks/useAction';
import { useFocusAfterReload } from '@/hooks/useFocusAfterReload';
import { useT } from '@/languages/useT';

import styles from './NameListStyle.module.css';
import translations from './NameListTranslation.json';

// Longest name of a genre or a language: Name of catalog_schemas.py
const NAME_MAX_LENGTH = 50;

// A list of names to keep (the genres of a kind, the languages): add one, rename one in its place, delete one.
// onCreate(name), onRename(entry, name) and onDelete(entry) return the request; onChanged() reloads after any of them
export default function NameList({ title, entries, onCreate, onRename, onDelete, onChanged, deleteQuestion }) {
  const t = useT(translations);
  const { run, running } = useAction();
  const [name, setName] = useState('');
  const [editing, setEditing] = useState(null);
  const [newName, setNewName] = useState('');
  // The rename field when it is open, and the pencil of each entry: the focus goes to the field when it opens, and back
  // to the pencil of its entry when it closes
  const field = useRef(null);
  const pencils = useRef(new Map());
  const lastEdited = useRef(null);
  // A deleted entry takes its row away: the focus goes back to the title of the list
  const { target: heading, expect } = useFocusAfterReload(entries);

  useEffect(() => {
    if (editing) field.current?.focus();
    else if (lastEdited.current) pencils.current.get(lastEdited.current)?.focus();
    lastEdited.current = editing;
  }, [editing]);

  async function create(event) {
    event.preventDefault();
    if (!name.trim()) return;
    if (await run('create', () => onCreate(name.trim()), t('createFailed'))) {
      setName('');
      onChanged();
    }
  }

  async function rename(event, entry) {
    event.preventDefault();
    if (!newName.trim()) return;
    if (await run(entry.id, () => onRename(entry, newName.trim()), t('renameFailed'))) {
      setEditing(null);
      onChanged();
    }
  }

  async function remove(entry) {
    if (await run(entry.id, () => onDelete(entry), t('deleteFailed'))) {
      expect();
      onChanged();
    }
  }

  return (
    <section className={styles.list}>
      <h2 ref={heading} tabIndex={-1} className={styles.title}>
        {title}
      </h2>
      <ul className={styles.entries}>
        {entries.length === 0 && <li className={styles.none}>{t('none')}</li>}
        {entries.map((entry) => (
          <li key={entry.id} className={styles.entry}>
            {editing === entry.id ? (
              <form className={styles.inline} onSubmit={(event) => rename(event, entry)}>
                <input
                  ref={field}
                  className={styles.input}
                  aria-label={t('newName')}
                  value={newName}
                  maxLength={NAME_MAX_LENGTH}
                  onChange={(event) => setNewName(event.target.value)}
                  onKeyDown={(event) => event.key === 'Escape' && setEditing(null)}
                />
                <Button type="submit" loading={running === entry.id}>
                  {t('save')}
                </Button>
                <Button variant="ghost" onClick={() => setEditing(null)}>
                  {t('cancel')}
                </Button>
              </form>
            ) : (
              <>
                <span className={styles.name}>{entry.name}</span>
                <span className={styles.actions}>
                  <Button
                    ref={(node) => (node ? pencils.current.set(entry.id, node) : pencils.current.delete(entry.id))}
                    variant="ghost"
                    aria-label={t('rename', { name: entry.name })}
                    title={t('rename', { name: entry.name })}
                    onClick={() => {
                      setEditing(entry.id);
                      setNewName(entry.name);
                    }}
                  >
                    <Icon name="pencil" size={14} />
                  </Button>
                  <ConfirmButton variant="ghost" question={deleteQuestion} loading={running === entry.id} onConfirm={() => remove(entry)}>
                    <Icon name="trash" size={14} />
                    <span className="sr-only">{t('delete', { name: entry.name })}</span>
                  </ConfirmButton>
                </span>
              </>
            )}
          </li>
        ))}
      </ul>
      <form className={styles.inline} onSubmit={create}>
        <input
          className={styles.input}
          aria-label={t('add', { list: title })}
          placeholder={t('placeholder')}
          value={name}
          maxLength={NAME_MAX_LENGTH}
          onChange={(event) => setName(event.target.value)}
        />
        <Button type="submit" variant="secondary" loading={running === 'create'}>
          <Icon name="plus" size={14} />
          {t('addButton')}
        </Button>
      </form>
    </section>
  );
}
