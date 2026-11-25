import { useState } from 'react';
import { useLocation } from 'react-router';

import Button from '@/components/Button/Button';
import Field from '@/components/Field/Field';
import Notice from '@/components/Notice/Notice';
import AuthCard from '@/features/auth/components/AuthCard/AuthCard';
import { isEmail } from '@/features/auth/validation';
import { useSubmit } from '@/hooks/useSubmit';
import { useT } from '@/languages/useT';
import { api } from '@/utils/api';

import translations from './ForgotPasswordPageTranslation.json';

// Asks for a link to choose a new password. The answer is the same whether the email has an account or not: nobody
// can find out who reads at the library
export default function ForgotPasswordPage() {
  const t = useT(translations);
  const location = useLocation();
  const { submit, sending, error } = useSubmit();
  const [email, setEmail] = useState(location.state?.email ?? '');
  const [invalid, setInvalid] = useState(null);
  const [sent, setSent] = useState(null);

  async function send(event) {
    event.preventDefault();
    if (!isEmail(email)) {
      setInvalid(t('emailInvalid'));
      return;
    }
    setInvalid(null);
    const { data } = await submit(() => api.post('/auth/password/forgot', { email: email.trim() }));
    if (data) setSent(data.message);
  }

  return (
    <AuthCard title={t('title')} lead={t('lead')}>
      {sent ? (
        <Notice tone="mail">{sent}</Notice>
      ) : (
        <form onSubmit={send} noValidate>
          <Field
            label={t('email')}
            type="email"
            autoComplete="email"
            value={email}
            error={invalid}
            onChange={(event) => setEmail(event.target.value)}
          />
          {error && <Notice tone="error">{error.message}</Notice>}
          <Button type="submit" size="large" full loading={sending}>
            {t('submit')}
          </Button>
        </form>
      )}
      <Button variant="link" to="/login">
        {t('back')}
      </Button>
    </AuthCard>
  );
}
