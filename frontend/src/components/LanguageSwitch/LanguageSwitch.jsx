import { LANGUAGES } from '@/languages/languages';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';

import styles from './LanguageSwitchStyle.module.css';
import translations from './LanguageSwitchTranslation.json';

// Each language written in itself: whoever doesn't understand the page still finds theirs
const NAMES = { ca: 'Català', es: 'Castellano', en: 'English' };

// The three languages in a row, the current one marked: changing it repaints the page and the API answers in it
export default function LanguageSwitch() {
  const t = useT(translations);
  const { language, setLanguage } = useLanguage();

  return (
    <div className={styles.switch} role="group" aria-label={t('label')}>
      {LANGUAGES.map((option) => (
        <button
          key={option}
          type="button"
          lang={option}
          className={styles.option}
          aria-pressed={option === language}
          onClick={() => setLanguage(option)}
        >
          {NAMES[option]}
        </button>
      ))}
    </div>
  );
}
