
#include <linux/version.h>

/*
 * Although kswapd allows for reclaiming pages by scanning nodes it does not
 * allow for targeting the reclaim of a single page regardless of what zone
 * the page resides in. This function exists to enable that functionality.
 * Must be executed with appropriate node locking, see balance_pgdat
 * or caller for example.
 */
static unsigned long reclaim_page(struct page *p, struct scan_control *sc)
{
	unsigned long nr_reclaimed = 0;
	unsigned int pagezoneid = 0;
	unsigned long nr_zone_taken[MAX_NR_ZONES] = { 0 };
	LIST_HEAD(node_page_list);
	struct reclaim_stat dummy_stat;
	struct page *page = p;
	pg_data_t *pgdat;
	struct lruvec *lruvec;
	spinlock_t *lru_lock;
	struct list_head *srclruptr;
	enum lru_list srclruid;
	unsigned int nr_pages = 0;
	pgdat = page_pgdat(page);
	lruvec = mem_cgroup_page_lruvec(page, pgdat);
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 11, 0)
	lru_lock = &lruvec->lru_lock;
#else
	lru_lock = &pgdat->lru_lock;
#endif
	srclruptr = &page->lru;
	INIT_LIST_HEAD(&node_page_list);

	spin_lock_irq(lru_lock);
	srclruid = page_lru(page);
	pagezoneid = page_zone_id(page);
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
	nr_pages = compound_nr(page);
#else
	if (PageHead(page)) {
		nr_pages = (1 << compound_order(page));
	} else {
		nr_pages = 1;
	}
#endif

	if (list_is_singular(srclruptr)) {
		/* There is only one page here, just leave it alone!
		 * We can't benefit from freeing one page, and removing the last page can be terrible.
		 */
		spin_unlock_irq(lru_lock);
		return 0;
	}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 11, 0)
	switch (__isolate_lru_page_prepare(page, 0)) {
	case 0:
		/*
		 * Be careful not to clear PageLRU until after we're
		 * sure the page is not being freed elsewhere -- the
		 * page release code relies on it.
		 */
		if (unlikely(!get_page_unless_zero(page))) {
			spin_unlock_irq(lru_lock);
			break;
		}
		if (!TestClearPageLRU(page)) {
			/*
			 * This page may in other isolation path,
			 * but we still hold lru_lock.
			 */
			put_page(page);
			spin_unlock_irq(lru_lock);
			break;
		}

#else
	switch (__isolate_lru_page(page, 0)) {
	case 0:
#endif
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
		ClearPageActive(page);
#endif
		list_move(&page->lru, &node_page_list);
		nr_zone_taken[pagezoneid] = nr_pages;
		update_lru_sizes(lruvec, srclruid, nr_zone_taken);
		spin_unlock_irq(lru_lock);
		/* at this point, we have isolated our target page (if head page then compound page) */

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
		nr_reclaimed += shrink_page_list(&node_page_list, pgdat, sc,
						 &dummy_stat, false);
#else
#ifdef UBUNTU_5_8_0_HACK
		nr_reclaimed += shrink_page_list(&node_page_list, pgdat, sc,
						 &dummy_stat, false);
#else
		nr_reclaimed += shrink_page_list(&node_page_list, pgdat, sc, 0,
						 &dummy_stat, false);
#endif
#endif
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
		spin_lock_irq(lru_lock);
		move_pages_to_lru(lruvec, &node_page_list);
		spin_unlock_irq(lru_lock);
#else
		// TODO: verify locking for this case, although practical testing suggests this is probably okay.
		while (!list_empty(&node_page_list)) {
			page = lru_to_page(&node_page_list);
			list_del(&page->lru);
			putback_lru_page(page);
		}
#endif
		break;
	default:
		spin_unlock_irq(lru_lock);
		//printk(KERN_INFO "Error Isolating Page for injected reclaim\n");
	}
	return nr_reclaimed;
}

extern int request_reclaim_flusher_wakeup(void)
{
	wakeup_flusher_threads(WB_REASON_VMSCAN);
	return 0;
}
EXPORT_SYMBOL(request_reclaim_flusher_wakeup);

/*
 * This function exists to enable the ability to follow the structure of balance_pgdat
 * but instead of throttling based on watermarks, scan levels, and priority,
 * we simply follow the directive to attempt the reclamation of a single page.
 * At the end we call the normal balance pgdat to give an opportunity to correct
 * impact to balance that this may have caused without delay.
 */
extern int inject_reclaim_page(pg_data_t *pgdat, int order, int classzone_idx,
			       struct page *page)
{
	unsigned long nr_soft_scanned;
	unsigned long nr_reclaimed = 0;
	struct scan_control sc = {
		.gfp_mask = GFP_KERNEL,
		.order = order,
		.may_unmap = 1,
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
		.may_swap = 1,
#endif
	};
	/*
	 * Begin necessary node isolation
	 */
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
	set_task_reclaim_state(current, &sc.reclaim_state);
#endif
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
	__fs_reclaim_acquire();
#else
	fs_reclaim_acquire(GFP_KERNEL);
#endif
	count_vm_event(PAGEOUTRUN);

	/* We don't want to alter watermarks at all, we just want to
	 * reclaim a specific page that is a great candidate for swapping.
	 */

	sc.priority = DEF_PRIORITY;
	do {
		bool raise_priority = true;

		sc.reclaim_idx = classzone_idx;

		/*
		 * If we have decided to call this function it
		 * means that we very directly want to swap or writeback
		 * whatever page was passed in, so we enable those flags in sc.
		 */
		sc.may_writepage = 1;
		sc.may_swap = 1;

		/*
		 * Do some background aging of the anon list, to give
		 * pages a chance to be referenced before reclaiming. All
		 * pages are rotated regardless of classzone as this is
		 * about consistent aging.
		 */
		age_active_anon(pgdat, &sc);

		/*
		 * we are skipping all limited reclaims, instead we just mark
		 * that no scanning has occurred
		 */
		sc.nr_scanned = 0;
		nr_soft_scanned = 0;
		/*
		 * As long as the page is mapped, attempt to reclaim it
		 * this is often called twice as a page needs to be aged out.
		 */
		nr_reclaimed += reclaim_page(page, &sc);
		/*
		 * This exit case statement needs improvement, we are simply
		 * capping our reclaim attempts and functioning blindly until
		 * we have either succeeded or not. Additional attempts after
		 * success should be noops or exit early
		 */
		if (raise_priority || !nr_reclaimed)
			sc.priority--;
	} while (sc.priority >= 1 && nr_reclaimed == 0);

	/*
	 * Undo all node isolation
	 */
	snapshot_refaults(NULL, pgdat);
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
	__fs_reclaim_release();
#else
	fs_reclaim_release(GFP_KERNEL);
#endif
#if LINUX_VERSION_CODE > KERNEL_VERSION(4, 20, 99)
	set_task_reclaim_state(current, NULL);
#endif

	return nr_reclaimed;
}
EXPORT_SYMBOL(inject_reclaim_page);
