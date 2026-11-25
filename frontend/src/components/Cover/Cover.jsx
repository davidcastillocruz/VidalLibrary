import { useState } from 'react';

import { API_URL } from '@/utils/api';

import styles from './CoverStyle.module.css';

// Colors of the covers drawn when a work has none: the cloths of old bindings, with the blue and the orange of the
// institute. The same in both themes, a cover is a physical object. Each work always gets the same one, from its id
const CLOTHS = ['#20447d', '#9c420e', '#2f5a45', '#7a2e2a', '#163159', '#a5772c', '#4f4a63', '#3c5c66'];

function clothOf(id) {
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return CLOTHS[hash % CLOTHS.length];
}

// The cover of a work: its image (GET /catalog/items/{id}/cover), or one drawn from its title in the style of its kind:
// a cloth binding for a book, a poster for a film, a box lid for a board game. The address carries the version of the
// cover (item.cover): the browser keeps each one for good, and a new cover is a new address. size: 'tiny' for the
// rows of a list (no text), 'small' for the grid, 'large' for its own page
export default function Cover({ item, size }) {
  // The version whose image failed (a file that went missing): a new cover is tried again
  const [broken, setBroken] = useState(null);
  const classes = [styles.cover, styles[item.kind], size && styles[size]].filter(Boolean).join(' ');

  if (item.cover && broken !== item.cover) {
    return (
      <div className={classes}>
        <img
          className={styles.image}
          src={`${API_URL}/catalog/items/${item.id}/cover?v=${item.cover}`}
          alt=""
          loading="lazy"
          onError={() => setBroken(item.cover)}
        />
      </div>
    );
  }
  return (
    <div className={`${classes} ${styles.drawn}`} style={{ '--cloth': clothOf(item.id) }} aria-hidden="true">
      <span className={styles.title}>{item.title}</span>
      <span className={styles.creator}>{item.creator}</span>
    </div>
  );
}
