import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router';

import Button from '@/components/Button/Button';
import Field from '@/components/Field/Field';
import Notice from '@/components/Notice/Notice';
import AuthCard from '@/features/auth/components/AuthCard/AuthCard';
import PasswordField from '@/features/auth/components/PasswordField/PasswordField';
import { useCurrentUser } from '@/features/auth/currentUser/useCurrentUser';
import { isEmail, PASSWORD_MAX_LENGTH } from '@/features/auth/validation';
import { useSubmit } from '@/hooks/useSubmit';
import { useT } from '@/languages/useT';
import { api } from '@/utils/api';

import translations from './LoginPageTranslation.json';

// Where to go after signing in: back to the page that asked for it, only if it is a page of this app
function safeReturn(from) {
  return typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/';
}

// Signing in with the email and the password the reader chose from its invitation. There's no sign-up: the
// accounts are made by the library. A notice in the state (a password just chosen) shows above the form
export default function LoginPage() {
  const t = useT(translations);
  const { user, refresh } = useCurrentUser();
  const navigate = useNavigate();
  const location = useLocation();
  const { submit, sending, error } = useSubmit();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [invalid, setInvalid] = useState({});

  // Already signed in: the form has nothing to do (but while signing in, the navigation below takes over)
  if (user && !sending) return <Navigate to={safeReturn(location.state?.from)} replace />;

  async function signIn(event) {
    event.preventDefault();
    const found = {};
    if (!isEmail(email)) found.email = t('emailInvalid');
    if (!password) found.password = t('passwordMissing');
    setInvalid(found);
    if (Object.keys(found).length) return;

    const { data } = await submit(() => api.post('/auth/login', { email: email.trim(), password }));
    if (!data) return;
    await refresh();
    navigate(safeReturn(location.state?.from), { replace: true });
  }

  return (
    <AuthCard title={t('title')} lead={t('lead')}>
      {location.state?.notice && <Notice tone="success">{location.state.notice}</Notice>}
      <form onSubmit={signIn} noValidate>
        <Field
          label={t('email')}
          type="email"
          autoComplete="email"
          value={email}
          error={invalid.email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <PasswordField
          label={t('password')}
          autoComplete="current-password"
          maxLength={PASSWORD_MAX_LENGTH}
          value={password}
          error={invalid.password}
          action={
            <Link to="/password/forgot" state={{ email }}>
              {t('forgot')}
            </Link>
          }
          onChange={(event) => setPassword(event.target.value)}
        />
        {error && <Notice tone="error">{error.message}</Notice>}
        <Button type="submit" size="large" full loading={sending}>
          {t('submit')}
        </Button>
      </form>
    </AuthCard>
  );
}
