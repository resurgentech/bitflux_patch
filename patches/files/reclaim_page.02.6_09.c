extern int request_reclaim_flusher_wakeup(void)
{
	wakeup_flusher_threads(WB_REASON_VMSCAN);
	return 0;
}
EXPORT_SYMBOL(request_reclaim_flusher_wakeup);


#define ERR_SWAPHINTS_ISOLATE_LRU 100
#define ERR_SWAPHINTS_UNEVICTABLE 101
#define ERR_SWAPHINTS_TAIL 102
#define ERR_SWAPHINTS_NOPAGE 103
#define ERR_SWAPHINTS_NOFOLIO 104
#define ERR_SWAPHINTS_TRY_GET 105
#define ERR_SWAPHINTS_FOLIO_MISMATCH 106
#define ERR_SWAPHINTS_TEST_LRU1 107
#define ERR_SWAPHINTS_TEST_LRU2 108

// TODO: this include should be at the top
#include <linux/page_idle.h>
extern unsigned long reclaim_page(struct folio *folio)
{
	int retval;
	LIST_HEAD(folio_list);

	folio_clear_referenced(folio);
	folio_test_clear_young(folio);

	if (!folio_isolate_lru(folio)) {
		folio_put(folio);
		return -ERR_SWAPHINTS_ISOLATE_LRU;
	}

	if (folio_test_unevictable(folio)) {
		folio_putback_lru(folio);
		folio_put(folio);
		return -ERR_SWAPHINTS_UNEVICTABLE;
	}

	list_add(&folio->lru, &folio_list);
	folio_put(folio);

	retval = reclaim_pages(&folio_list, true);
	return retval;
}
EXPORT_SYMBOL(reclaim_page);

