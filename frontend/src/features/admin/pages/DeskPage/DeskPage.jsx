import Button from '@/components/Button/Button';
import ConfirmButton from '@/components/ConfirmButton/ConfirmButton';
import Icon from '@/components/Icon/Icon';
import Notice from '@/components/Notice/Notice';
import Pagination from '@/components/Pagination/Pagination';
import PickupForm from '@/features/admin/components/PickupForm/PickupForm';
import { useAction } from '@/features/admin/hooks/useAction';
import LoanRow from '@/features/loans/components/LoanRow/LoanRow';
import { useFocusAfterReload } from '@/hooks/useFocusAfterReload';
import { SEARCH_MAX_LENGTH, useLastPage, useListParams } from '@/hooks/useListParams';
import { useRequest } from '@/hooks/useRequest';
import { useT } from '@/languages/useT';
import { api } from '@/utils/api';
import shared from '@/features/admin/adminStyles.module.css';

import translations from './DeskPageTranslation.json';

// Loans in each page of the desk: PAGE_SIZE of loan_management_service.py
const PAGE_SIZE = 30;
// The loans the desk can show, in the order of its filters: show of AdminLoanQuery in loan_schemas.py
const SHOWS = ['open', 'requested', 'active', 'overdue', 'all'];

// The loan desk: the reservations to hand over and the loans to receive, by reader or title
export default function DeskPage() {
  const t = useT(translations);
  const { params, change, search, setSearch } = useListParams();
  const show = params.get('show') ?? 'open';
  const q = params.get('q') ?? '';
  const page = Number(params.get('page')) || 1;
  const { run, running } = useAction();

  const { data, error, reload } = useRequest('/admin/loans', { show, q, page });
  useLastPage(page, data?.total, PAGE_SIZE, change);

  // The buttons of a loan change once it is handed over, returned or cancelled: the focus goes to the count of the list
  const { target: count, expect } = useFocusAfterReload(data);

  async function act(loan, action, body) {
    await run(`${loan.id}-${action}`, () => api.post(`/admin/loans/${loan.id}/${action}`, body), t(`${action}Failed`));
    expect();
    reload();
  }

  return (
    <main className={shared.page}>
      <title>{`${t('title')} · Biblioteca Vidal i Barraquer`}</title>
      <div className={shared.heading}>
        <div>
          <h1>{t('title')}</h1>
          <p className={shared.lead}>{t('lead')}</p>
        </div>
      </div>

      <div className={shared.toolbar}>
        <label className={shared.search}>
          <Icon name="search" size={18} />
          <span className="sr-only">{t('search')}</span>
          <input
            type="search"
            value={search}
            maxLength={SEARCH_MAX_LENGTH}
            placeholder={t('searchPlaceholder')}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <div className={shared.chips} role="group" aria-label={t('show')}>
          {SHOWS.map((option) => (
            <button
              key={option}
              type="button"
              className={shared.chip}
              aria-pressed={show === option}
              onClick={() => change({ show: option === 'open' ? '' : option })}
            >
              {t(option)}
            </button>
          ))}
        </div>
      </div>

      {error && <Notice tone="error">{t('failed')}</Notice>}

      {data && (
        <>
          <p ref={count} tabIndex={-1} className={shared.count}>
            {t(data.total === 1 ? 'countOne' : 'count', { count: data.total })}
          </p>
          {data.loans.length === 0 ? (
            <p className={shared.empty}>{t('empty')}</p>
          ) : (
            <ul className={shared.list}>
              {data.loans.map((loan) => (
                <LoanRow
                  key={loan.id}
                  loan={loan}
                  details={
                    <p className={shared.reader}>
                      {loan.reader.name} <span>· {loan.reader.email}</span>
                    </p>
                  }
                >
                  {loan.status === 'requested' && (
                    <>
                      <PickupForm
                        loading={running === `${loan.id}-pickup`}
                        onPickUp={(dueOn) => act(loan, 'pickup', { due_on: dueOn })}
                      />
                      <ConfirmButton
                        variant="ghost"
                        question={t('cancelQuestion')}
                        loading={running === `${loan.id}-cancel`}
                        onConfirm={() => act(loan, 'cancel')}
                      >
                        {t('cancel')}
                      </ConfirmButton>
                    </>
                  )}
                  {loan.status === 'active' && (
                    <Button loading={running === `${loan.id}-return`} onClick={() => act(loan, 'return')}>
                      <Icon name="check" size={16} />
                      {t('return')}
                    </Button>
                  )}
                </LoanRow>
              ))}
            </ul>
          )}
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(next) => change({ page: next })} />
        </>
      )}
    </main>
  );
}
