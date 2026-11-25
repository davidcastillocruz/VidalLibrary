import { Link } from 'react-router';

import styles from './ButtonStyle.module.css';

// Button of the style guide. variant: primary (one per view, the action the user came for), secondary for the
// alternatives, ghost for what matters little, link to navigate and danger for what can't be undone easily.
// size: 'large' for the main forms and the hero. With to it's a link inside the app, with href a link outside it,
// a <button> otherwise.
// loading shows a spinner next to the text, so the button keeps saying what it does, and ignores the presses meanwhile.
// disabled looks off and ignores them too. Neither is the disabled attribute: a disabled button loses the focus, and
// the keyboard would go back to the top of the page (Next on the last page, Reserve with the last copy taken)
export default function Button({
  variant = 'primary',
  size,
  full = false,
  loading = false,
  to,
  href,
  className,
  children,
  onClick,
  disabled = false,
  ...props
}) {
  const classes = [styles.button, styles[variant], size && styles[size], full && styles.full, className]
    .filter(Boolean)
    .join(' ');

  if (to) {
    return (
      <Link to={to} className={classes} onClick={onClick} {...props}>
        {children}
      </Link>
    );
  }
  if (href) {
    return (
      <a href={href} className={classes} onClick={onClick} {...props}>
        {children}
      </a>
    );
  }
  return (
    <button
      type="button"
      {...props}
      className={classes}
      aria-disabled={loading || disabled || undefined}
      aria-busy={loading || undefined}
      // A press while it saves or while it's off does nothing, a submit included: the form isn't sent twice
      onClick={loading || disabled ? (event) => event.preventDefault() : onClick}
    >
      {loading && <span className={styles.spinner} aria-hidden="true" />}
      {children}
    </button>
  );
}
