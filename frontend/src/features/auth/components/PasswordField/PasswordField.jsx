import { useState } from 'react';

import Field from '@/components/Field/Field';
import Icon from '@/components/Icon/Icon';
import { useT } from '@/languages/useT';

import styles from './PasswordFieldStyle.module.css';
import translations from './PasswordFieldTranslation.json';

// Password field with a button to show what was typed, so it doesn't need typing twice. Other props go to Field
export default function PasswordField(props) {
  const t = useT(translations);
  const [visible, setVisible] = useState(false);

  return (
    <Field
      {...props}
      type={visible ? 'text' : 'password'}
      trailing={
        <button
          type="button"
          className={styles.reveal}
          aria-label={t(visible ? 'hide' : 'show')}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
        >
          <Icon name={visible ? 'eyeOff' : 'eye'} size={18} />
        </button>
      }
    />
  );
}
