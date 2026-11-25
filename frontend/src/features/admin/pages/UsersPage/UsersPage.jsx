import { useEffect, useRef, useState } from 'react';

import Button from '@/components/Button/Button';
import ConfirmButton from '@/components/ConfirmButton/ConfirmButton';
import Field from '@/components/Field/Field';
import Icon from '@/components/Icon/Icon';
import Notice from '@/components/Notice/Notice';
import Pagination from '@/components/Pagination/Pagination';
import Select from '@/components/Select/Select';
import { useAction } from '@/features/admin/hooks/useAction';
import { useCurrentUser } from '@/features/auth/currentUser/useCurrentUser';
import { isEmail, NAME_MAX_LENGTH } from '@/features/auth/validation';
import { useFocusAfterReload } from '@/hooks/useFocusAfterReload';
import { SEARCH_MAX_LENGTH, useLastPage, useListParams } from '@/hooks/useListParams';
import { useRequest } from '@/hooks/useRequest';
import { useT } from '@/languages/useT';
import { api } from '@/utils/api';
import shared from '@/features/admin/adminStyles.module.css';

import styles from './UsersPageStyle.module.css';
import translations from './UsersPageTranslation.json';

// Accounts in each page: PAGE_SIZE of user_management_service.py
const PAGE_SIZE = 30;

// The form of a new account: its owner gets an invitation to choose a password
function NewUser({ onCreated }) {
  const t = useT(translations);
  const { run, running } = useAction();
  const [form, setForm] = useState({ email: '', name: '', role: 'reader' });
  const [invalid, setInvalid] = useState({});

  async function create(event) {
    event.preventDefault();
    const found = {};
    if (!isEmail(form.email)) found.email = t('emailInvalid');
    if (!form.name.trim()) found.name = t('nameMissing');
    setInvalid(found);
    if (Object.keys(found).length) return;
    const body = { ...form, email: form.email.trim() };
    if (await run('create', () => api.post('/admin/users', body), t('createFailed'))) {
      setForm({ email: '', name: '', role: 'reader' });
      onCreated();
    }
  }

  return (
    <form className={`${shared.panel} ${styles.newUser}`} onSubmit={create} noValidate>
      <h2>{t('newTitle')}</h2>
      <p className={styles.help}>{t('newHelp')}</p>
      <div className={styles.newFields}>
        <Field
          label={t('email')}
          type="email"
          value={form.email}
          error={invalid.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <Field
          label={t('name')}
          value={form.name}
          maxLength={NAME_MAX_LENGTH}
          error={invalid.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <Select
          label={t('role')}
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
          options={[
            { value: 'reader', label: t('reader') },
            { value: 'librarian', label: t('librarian') },
          ]}
        />
        <Button type="submit" size="large" loading={running === 'create'} className={styles.newSubmit}>
          <Icon name="send" size={16} />
          {t('invite')}
        </Button>
      </div>
    </form>
  );
}

// One account in the list, with its changes. self: the librarian looking, who can't delete itself or lose its role.
// Editing it, the focus goes to its name, and back to the pencil when the form closes. onDeleted() once it is deleted:
// its row goes away with the focus
function UserRow({ user, self, onChanged, onDeleted }) {
  const t = useT(translations);
  const { run, running } = useAction();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: user.name, role: user.role });
  const nameField = useRef(null);
  const pencil = useRef(null);
  const opened = useRef(false);

  useEffect(() => {
    if (editing) nameField.current?.focus();
    else if (opened.current) pencil.current?.focus();
    opened.current = editing;
  }, [editing]);

  // The form starts from the account as it is now, not as it was the last time it opened
  function edit() {
    setForm({ name: user.name, role: user.role });
    setEditing(true);
  }

  async function save(event) {
    event.preventDefault();
    if (!form.name.trim()) return;
    if (await run('save', () => api.put(`/admin/users/${user.id}`, form), t('saveFailed'))) {
      setEditing(false);
      onChanged();
    }
  }

  async function invite() {
    await run('invite', () => api.post(`/admin/users/${user.id}/invitation`), t('inviteFailed'));
  }

  async function remove() {
    if (await run('delete', () => api.delete(`/admin/users/${user.id}`), t('deleteFailed'))) onDeleted();
  }

  if (editing) {
    return (
      <li className={styles.row}>
        <form className={styles.edit} onSubmit={save}>
          <Field
            ref={nameField}
            label={t('name')}
            value={form.name}
            maxLength={NAME_MAX_LENGTH}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Select
            label={t('role')}
            value={form.role}
            disabled={self}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            options={[
              { value: 'reader', label: t('reader') },
              { value: 'librarian', label: t('librarian') },
            ]}
          />
          <div className={styles.editActions}>
            <Button type="submit" loading={running === 'save'}>
              {t('save')}
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              {t('cancel')}
            </Button>
          </div>
        </form>
      </li>
    );
  }

  return (
    <li className={styles.row}>
      <div className={styles.who}>
        <p className={styles.name}>
          {user.name}
          {self && <span className={styles.you}>{t('you')}</span>}
        </p>
        <p className={styles.email}>{user.email}</p>
        <p className={styles.badges}>
          {user.role === 'librarian' && <span className={styles.badge}>{t('librarian')}</span>}
          {user.invited && <span className={`${styles.badge} ${styles.pending}`}>{t('pending')}</span>}
          {user.open_loans > 0 && (
            <span className={styles.loans}>{t(user.open_loans === 1 ? 'loansOne' : 'loans', { count: user.open_loans })}</span>
          )}
        </p>
      </div>
      <div className={styles.actions}>
        {user.invited && (
          <Button variant="secondary" loading={running === 'invite'} onClick={invite}>
            {t('resend')}
          </Button>
        )}
        <Button ref={pencil} variant="ghost" onClick={edit} aria-label={t('edit', { name: user.name })} title={t('edit', { name: user.name })}>
          <Icon name="pencil" size={14} />
        </Button>
        {!self && (
          <ConfirmButton variant="ghost" question={t('deleteQuestion')} loading={running === 'delete'} onConfirm={remove}>
            <Icon name="trash" size={14} />
            <span className="sr-only">{t('delete', { name: user.name })}</span>
          </ConfirmButton>
        )}
      </div>
    </li>
  );
}

// The accounts of the library: who can reserve and who runs the desk. There's no sign-up, they are made here
export default function UsersPage() {
  const t = useT(translations);
  const { user: me } = useCurrentUser();
  const { params, change, search, setSearch } = useListParams();
  const role = params.get('role') ?? '';
  const q = params.get('q') ?? '';
  const page = Number(params.get('page')) || 1;

  const { data, error, reload } = useRequest('/admin/users', { role, q, page });
  // A deleted account takes its row away: the focus goes back to the title
  const { target: title, expect } = useFocusAfterReload(data);
  useLastPage(page, data?.total, PAGE_SIZE, change);

  return (
    <main className={shared.page}>
      <title>{`${t('title')} · Biblioteca Vidal i Barraquer`}</title>
      <div className={shared.heading}>
        <div>
          <h1 ref={title} tabIndex={-1}>
            {t('title')}
          </h1>
          <p className={shared.lead}>{t('lead')}</p>
        </div>
      </div>

      <NewUser onCreated={reload} />

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
        <div className={shared.chips} role="group" aria-label={t('role')}>
          {['', 'reader', 'librarian'].map((option) => (
            <button
              key={option || 'all'}
              type="button"
              className={shared.chip}
              aria-pressed={role === option}
              onClick={() => change({ role: option })}
            >
              {option ? t(`${option}s`) : t('all')}
            </button>
          ))}
        </div>
      </div>

      {error && <Notice tone="error">{t('failed')}</Notice>}

      {data && (
        <>
          {data.users.length === 0 ? (
            <p className={shared.empty}>{t('empty')}</p>
          ) : (
            <ul className={shared.list}>
              {data.users.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  self={user.id === me?.id}
                  onChanged={reload}
                  onDeleted={() => {
                    expect();
                    reload();
                  }}
                />
              ))}
            </ul>
          )}
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(next) => change({ page: next })} />
        </>
      )}
    </main>
  );
}
