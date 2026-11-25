import Icon from '@/components/Icon/Icon';

import styles from './NoticeStyle.module.css';

// The icon of each tone, so the tone isn't told by color alone
const ICONS = { error: 'alert', success: 'check', info: 'info', mail: 'mail' };

// A message inside the page, next to what it talks about: the error of a form, a link that was sent, a password
// that changed. tone: error, success, info or mail. An error is announced at once, the rest when the reader is free
export default function Notice({ tone = 'info', title, children }) {
  return (
    <div className={`${styles.notice} ${styles[tone]}`} role={tone === 'error' ? 'alert' : 'status'}>
      <span className={styles.icon}>
        <Icon name={ICONS[tone]} size={14} />
      </span>
      <div className={styles.body}>
        {title && <p className={styles.title}>{title}</p>}
        {children && <p className={styles.text}>{children}</p>}
      </div>
    </div>
  );
}
