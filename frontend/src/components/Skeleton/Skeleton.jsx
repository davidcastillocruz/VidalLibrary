import styles from './SkeletonStyle.module.css';

// The shape of what is loading, while it loads: a page that stays blank looks broken. shape: 'cover' (a 2:3 cover),
// 'line' (a line of text, width as a CSS length) or 'title' (a taller line). Hidden from screen readers: the region
// that loads says it is busy (aria-busy)
export default function Skeleton({ shape = 'line', width }) {
  return <span className={`${styles.skeleton} ${styles[shape]}`} style={width ? { width } : undefined} aria-hidden="true" />;
}
