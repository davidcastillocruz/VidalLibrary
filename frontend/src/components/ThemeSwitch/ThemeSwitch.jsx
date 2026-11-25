import Icon from '@/components/Icon/Icon';
import { useT } from '@/languages/useT';
import { useTheme } from '@/themes/useTheme';

import styles from './ThemeSwitchStyle.module.css';
import translations from './ThemeSwitchTranslation.json';

// Switches between the light theme and the dark one. It shows the theme it switches to
export default function ThemeSwitch() {
  const t = useT(translations);
  const { theme, setTheme } = useTheme();
  const next = theme === 'dark' ? 'light' : 'dark';

  return (
    <button
      type="button"
      className={styles.switch}
      aria-label={t(next === 'light' ? 'toLight' : 'toDark')}
      title={t(next === 'light' ? 'toLight' : 'toDark')}
      onClick={() => setTheme(next)}
    >
      <Icon name={next === 'light' ? 'sun' : 'moon'} size={18} />
    </button>
  );
}
