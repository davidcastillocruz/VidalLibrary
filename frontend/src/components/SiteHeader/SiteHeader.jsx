import { NavLink, useLocation, useNavigate } from 'react-router';

import Button from '@/components/Button/Button';
import Icon from '@/components/Icon/Icon';
import { useCurrentUser } from '@/features/auth/currentUser/useCurrentUser';
import { useSignOut } from '@/features/auth/currentUser/useSignOut';
import { useT } from '@/languages/useT';

import styles from './SiteHeaderStyle.module.css';
import translations from './SiteHeaderTranslation.json';

// Three spines on a shelf, the mark of the library
function Mark() {
  return (
    <svg className={styles.mark} viewBox="0 0 28 28" aria-hidden="true">
      <rect x="4" y="6" width="5" height="17" rx="1" />
      <rect x="10.5" y="3" width="5" height="20" rx="1" />
      <rect x="17.5" y="7.5" width="5" height="16" rx="1" transform="rotate(-12 20 15.5)" />
      <path d="M2 24.5h24" />
    </svg>
  );
}

// The top of every page, like the one of the institute's website: a band with the institute, then the name of the
// library, the sections the user can open and its session.
// A guest sees the catalog and how to sign in; a reader its loans too; a librarian the management as well
export default function SiteHeader() {
  const t = useT(translations);
  const { user } = useCurrentUser();
  const signOut = useSignOut();
  const navigate = useNavigate();
  const location = useLocation();

  const links = [{ to: '/', label: t('catalog'), end: true }];
  if (user) links.push({ to: '/loans', label: t('loans') });
  if (user?.role === 'librarian') links.push({ to: '/admin', label: t('admin') });

  async function leave() {
    if (await signOut()) navigate('/');
  }

  return (
    <header className={styles.header}>
      <div className={styles.band}>
        <div className={styles.bandInner}>
          <a href="https://www.vidalibarraquer.cat/" className={styles.school} target="_blank" rel="noreferrer">
            {t('school')}
          </a>
          <span className={styles.city}>Tarragona</span>
        </div>
      </div>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.brand}>
          <Mark />
          <span className={styles.name}>
            <span className={styles.small}>{t('library')}</span>
            Vidal i Barraquer
          </span>
        </NavLink>

        <nav className={styles.nav} aria-label={t('sections')}>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => [styles.link, isActive && styles.active].filter(Boolean).join(' ')}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className={styles.session}>
          {user === null && (
            <Button
              variant="secondary"
              to="/login"
              state={location.pathname === '/login' ? undefined : { from: location.pathname + location.search }}
            >
              {t('signIn')}
            </Button>
          )}
          {user && (
            <>
              <span className={styles.who}>
                <Icon name="user" size={16} />
                <span className={styles.whoName}>{user.name}</span>
              </span>
              <Button variant="ghost" onClick={leave} aria-label={t('signOut')} title={t('signOut')}>
                <Icon name="signOut" size={16} />
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
