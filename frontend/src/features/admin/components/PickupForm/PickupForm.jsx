import { useId, useState } from 'react';

import Button from '@/components/Button/Button';
import { useT } from '@/languages/useT';
import { addDays, libraryDay } from '@/utils/dates';

import styles from './PickupFormStyle.module.css';
import translations from './PickupFormTranslation.json';

// Usual length of a loan, in days: the due day the desk proposes
export const LOAN_DAYS = 21;
// Longest loan: MAX_LOAN_DAYS of loan_rules.py
const MAX_LOAN_DAYS = 90;

// Hands a reserved copy over: the day it has to come back by, from tomorrow to 90 days away, and the button
export default function PickupForm({ onPickUp, loading }) {
  const t = useT(translations);
  const id = useId();
  const today = libraryDay();
  const [dueOn, setDueOn] = useState(addDays(today, LOAN_DAYS));

  return (
    <form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        onPickUp(dueOn);
      }}
    >
      <label htmlFor={id} className={styles.label}>
        {t('dueOn')}
      </label>
      <input
        id={id}
        type="date"
        className={styles.date}
        value={dueOn}
        min={addDays(today, 1)}
        max={addDays(today, MAX_LOAN_DAYS)}
        required
        onChange={(event) => setDueOn(event.target.value)}
      />
      <Button type="submit" loading={loading}>
        {t('handOver')}
      </Button>
    </form>
  );
}
