import { useId } from 'react';

import Icon from '@/components/Icon/Icon';

import styles from './FieldStyle.module.css';

// Form field of the style guide: the label always visible above it, never only a placeholder, and the error under it
// with an icon, not only in red. action: a link on the line of the label ("¿La has olvidado?"). trailing: a control
// inside the field, on its right (show the password). className styles the <input>, where the rest of the props go
export default function Field({ label, error, help, action, trailing, id, className, ...inputProps }) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const messageId = `${inputId}-message`;
  const message = error || help;

  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <label htmlFor={inputId} className={styles.label}>
          {label}
        </label>
        {action}
      </div>
      <div className={styles.control}>
        <input
          id={inputId}
          className={[styles.input, trailing && styles.withTrailing, className].filter(Boolean).join(' ')}
          aria-invalid={error ? true : undefined}
          aria-describedby={message ? messageId : undefined}
          {...inputProps}
        />
        {trailing && <div className={styles.trailing}>{trailing}</div>}
      </div>
      {error ? (
        <p id={messageId} className={styles.error}>
          <Icon name="alert" size={14} />
          {error}
        </p>
      ) : (
        help && (
          <p id={messageId} className={styles.help}>
            {help}
          </p>
        )
      )}
    </div>
  );
}
