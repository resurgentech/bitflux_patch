
extern int request_reclaim_flusher_wakeup(void)
{
	wakeup_flusher_threads(WB_REASON_VMSCAN);
	return 0;
}
EXPORT_SYMBOL(request_reclaim_flusher_wakeup);

extern unsigned long reclaim_page(struct page *page)
{
	if (isolate_lru_page(page))
		return -EINVAL;

	if (PageUnevictable(page)) {
		putback_lru_page(page);
		return -EPERM;
	}

	LIST_HEAD(page_list);

	list_add(&page->lru, &page_list);

	return reclaim_pages(&page_list);
}
EXPORT_SYMBOL(reclaim_page);
