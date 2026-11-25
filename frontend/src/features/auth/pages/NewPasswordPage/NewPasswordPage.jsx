import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import Button from '@/components/Button/Button';
import Notice from '@/components/Notice/Notice';
import AuthCard from '@/features/auth/components/AuthCard/AuthCard';
import PasswordField from '@/features/auth/components/PasswordField/PasswordField';
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH } from '@/features/auth/validation';
import { useSubmit } from '@/hooks/useSubmit';
import { useT } from '@/languages/useT';
import { api } from '@/utils/api';

import translations from './NewPasswordPageTranslation.json';

// Choosing a password from the link of an email (?token=...). mode: 'invitation' for the first one of a new account,
// 'reset' for a new one. Both go through POST /auth/password/reset; then the reader signs in with it
export default function NewPasswordPage({ mode }) {
  const t = useT(translations);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token');
  const { submit, sending, error } = useSubmit();
  const [password, setPassword] = useState('');
  const [invalid, setInvalid] = useState(null);

  async function save(event) {
    event.preventDefault();
    if (password.length < PASSWORD_MIN_LENGTH) {
      setInvalid(t('tooShort', { min: PASSWORD_MIN_LENGTH }));
      return;
    }
    setInvalid(null);
    const { data } = await submit(() => api.post('/auth/password/reset', { token, password }));
    if (data) navigate('/login', { replace: true, state: { notice: data.message } });
  }

  return (
    <AuthCard title={t(`${mode}Title`)} lead={t(`${mode}Lead`)}>
      {token ? (
        <form onSubmit={save} noValidate>
          <PasswordField
            label={t('password')}
            autoComplete="new-password"
            maxLength={PASSWORD_MAX_LENGTH}
            value={password}
            error={invalid}
            help={t('help', { min: PASSWORD_MIN_LENGTH })}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && <Notice tone="error">{error.message}</Notice>}
          <Button type="submit" size="large" full loading={sending}>
            {t('submit')}
          </Button>
        </form>
      ) : (
        <Notice tone="error">{t('noToken')}</Notice>
      )}
    </AuthCard>
  );
}
