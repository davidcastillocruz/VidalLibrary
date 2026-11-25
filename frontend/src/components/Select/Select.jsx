import { useId } from 'react';

import Icon from '@/components/Icon/Icon';

import styles from './SelectStyle.module.css';

// A native <select> in the style of Field: the label always visible above it. options: [{ value, label }]
export default function Select({ label, options, id, className, hideLabel = false, ...selectProps }) {
  const generatedId = useId();
  const selectId = id ?? generatedId;

  return (
    <div className={[styles.field, className].filter(Boolean).join(' ')}>
      <label htmlFor={selectId} className={hideLabel ? 'sr-only' : styles.label}>
        {label}
      </label>
      <div className={styles.control}>
        <select id={selectId} className={styles.select} {...selectProps}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Icon name="down" size={16} className={styles.chevron} />
      </div>
    </div>
  );
}
