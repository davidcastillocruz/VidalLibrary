import styles from './AuthCardStyle.module.css';

// The card of the pages to get in: a title, what to do, and its form. Narrow, the forms are read on a phone
export default function AuthCard({ title, lead, children }) {
  return (
    <main className={styles.page}>
      <title>{`${title} · Biblioteca Vidal i Barraquer`}</title>
      <div className={styles.card}>
        <header className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          {lead && <p className={styles.lead}>{lead}</p>}
        </header>
        {children}
      </div>
    </main>
  );
}
