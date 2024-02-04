extern int request_reclaim_flusher_wakeup(void)
{
	wakeup_flusher_threads(WB_REASON_VMSCAN);
	return 0;
}
EXPORT_SYMBOL(request_reclaim_flusher_wakeup);

extern unsigned long reclaim_page(struct page *page)
{
	int retval;
	LIST_HEAD(page_list);

	if (PageTail(page))
		return -EPIPE;

	if (isolate_lru_page(page))
		return -EINVAL;

	if (PageUnevictable(page)) {
		putback_lru_page(page);
		return -EPERM;
	}

	list_add(&page->lru, &page_list);

	retval = reclaim_pages(&page_list);
	return retval;
}
EXPORT_SYMBOL(reclaim_page);

