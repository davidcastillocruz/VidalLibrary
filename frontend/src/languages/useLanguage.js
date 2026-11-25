import { use } from 'react';

import { LanguageContext } from './LanguageContext';

// Current language and setLanguage('ca' | 'es' | 'en'), in any component inside LanguageProvider
export function useLanguage() {
  const context = use(LanguageContext);
  if (!context) throw new Error('useLanguage must be used inside LanguageProvider');
  return context;
}
