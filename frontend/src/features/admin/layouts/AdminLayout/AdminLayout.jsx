import { NavLink, Outlet } from 'react-router';

import { useT } from '@/languages/useT';

import styles from './AdminLayoutStyle.module.css';
import translations from './AdminLayoutTranslation.json';

// The management of the library, for its librarians: the loan desk, the catalog, its lists and the accounts
export default function AdminLayout() {
  const t = useT(translations);
  const sections = [
    { to: '/admin/loans', label: t('loans') },
    { to: '/admin/catalog', label: t('catalog') },
    { to: '/admin/lists', label: t('lists') },
    { to: '/admin/users', label: t('users') },
  ];

  return (
    <div className={styles.admin}>
      <header className={styles.header}>
        <nav className={styles.tabs} aria-label={t('sections')}>
          {sections.map((section) => (
            <NavLink
              key={section.to}
              to={section.to}
              className={({ isActive }) => [styles.tab, isActive && styles.active].filter(Boolean).join(' ')}
            >
              {section.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
