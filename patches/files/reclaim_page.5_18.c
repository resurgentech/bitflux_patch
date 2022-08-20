
extern int request_reclaim_flusher_wakeup(void)
{
	wakeup_flusher_threads(WB_REASON_VMSCAN);
	return 0;
}
EXPORT_SYMBOL(request_reclaim_flusher_wakeup);

extern int reclaim_page(struct page *page)
{
	int output;
	unsigned long mapcount;
	u64 pfn;

	LIST_HEAD(page_list);

	list_add(&page->lru, &page_list);

	output = (int) reclaim_pages(&page_list);

	return output;
}
EXPORT_SYMBOL(reclaim_page);
