// SPDX-License-Identifier: GPL-2.0-only
/*
 * Authors: Lakshmanan Narayanan, Peter Weir
 * Maintainer: Peter Weir <peterjweir@gmail.com>
 * Copyright (C) 2021 Resurgent Technologies
 */

#include <linux/backing-dev-defs.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/page-flags.h>
#include <linux/pagemap.h>
#include <linux/page_idle.h>
#include <linux/pfn_t.h>
#include <linux/proc_fs.h>
#include <linux/swap.h>
#include <linux/uaccess.h>
#include <linux/version.h>
#include <linux/writeback.h>
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 17, 0)
#include <linux/slab.h>
#endif


MODULE_DESCRIPTION("Proc File Enabled Swap Hint Handler.");
#define VERSION_NUMBER "0.63"
MODULE_VERSION(VERSION_NUMBER);

#define BUFSIZE 1024
#define PROCFS_MAX_SIZE 1024
#define PGLIST_MAX_SIZE 1048576 //up to 4GB swapout
#define PROCFS_NAME "swaphints"

/**
 * This structure hold information about the /proc file
 *
 */
static struct proc_dir_entry *swaphints_proc_file;

/**
 * The buffer used to store character for this module
 *
 */
static unsigned long *swaphints_page_list;
static unsigned long *swaphints_page_offset;

/**
 * Debug switch
 *
 */
static int debug = 0;
module_param(debug, int, 0660);

/**
 * This function is called then the /proc file is read
 * We don't currently provide any real info, so we just return 0.
 */
static ssize_t swaphints_read(struct file *file, char *buffer, size_t count,
			      loff_t *data)
{
	int ret = 0;
	if (debug)
		printk(KERN_INFO "swaphints_read (/proc/%s) called\n",
		       PROCFS_NAME);

	if (count > 0) {
		ret = 0;
	}

	return ret;
}

/*
 * Internal Function to request the reclamation of a single specific page.
 *
 */
static int swaphints_swap_a_page(unsigned long pagenumber)
{
	struct page *page;
	u64 pfn = pagenumber;

	if (pfn == 0)
		return 0;
	page = pfn_to_page(pfn);

	if (!PageLRU(page))
		return 0;

	if (PageTransCompound(page)) {
		printk(KERN_INFO "pfn: %lu - page transparent\n", pfn);
		return 0;
	}

	mapcount = page_mapcount(page);
	if (mapcount != 1) {
		printk(KERN_INFO "pfn: %lu - page_mapcount() = %lu\n", pfn, mapcount);
		return 0;
	}


	ClearPageReferenced(page);
	test_and_clear_page_young(page);

	if (isolate_lru_page(page)){
		printk(KERN_INFO "pfn: %lu - failed isolate_lru_page\n", pfn);
		return 0;
	}

	if (PageUnevictable(page)) {
		printk(KERN_INFO "pfn: %lu - page unevictable\n", pfn);
		putback_lru_page(page);
		return 0;
	}

	return reclaim_page(page);
}

/**
 * Internal function to process a list of specific pages through individual
 * reclamation. After the list, and every few hundred pages we proactively
 * wakeup the flusher thread. This improves long term performance, and keeps
 * memory from being filled with reclaim pages and prevents the flusher from
 * hitting a state where it will have to stop and reclaim in a more aggressive
 * manner.
 */
static int swaphints_swap_the_pagelist(void)
{
	int pages_swapped = 0;
	int i;
	u64 pfn;

	for (i = 0; i < *swaphints_page_offset; i++) {
		pages_swapped += swaphints_swap_a_page(swaphints_page_list[i]);
		if ((i % 512) == 0)
			request_reclaim_flusher_wakeup();
	}
	request_reclaim_flusher_wakeup();
	return pages_swapped;
}

/**
 * This function is called with the /proc file is written
 * It accepts either a pfn in the form of a numeric decimal string (e.g.
 * "437895468") or the key word "swapnow" all other inputs are ignored.
 * subsequent numbers submitted are added to a list, and
 * swapnow will begin processing the list.
 * fs locking may be insufficient, and we may need to claim a lock on this
 * function to avoid altering the list of pages while being reclaimed.
 */
static ssize_t swaphints_write(struct file *file, const char __user *ubuf,
			       size_t count, loff_t *ppos)
{
	int num, c = 0;
	int swapped = 0;
	unsigned long bignumber;
	char *buf;
	if ((buf = kvzalloc(BUFSIZE, GFP_KERNEL)) == NULL)
		return -ENOMEM;
	if (*ppos > 0 || count > BUFSIZE) {
		kvfree(buf);
		return -EFAULT;
	}
	if (copy_from_user(buf, ubuf, count)) {
		kvfree(buf);
		return -EFAULT;
	}
	if (strstr(buf, "swapnow") != NULL) {
		swapped = 0;
		if (debug)
			printk(KERN_INFO
			       "Beginning swap attempt of %ld pages\n",
			       *swaphints_page_offset);
		if (*swaphints_page_offset > 0) {
			swapped = swaphints_swap_the_pagelist();
			*swaphints_page_offset = 0;
			if (debug)
				printk(KERN_INFO
				       "Swaphints reclaimed %d pages\n",
				       swapped);
		}
		c = strlen(buf);
		*ppos = c;
		kvfree(buf);
		return c;
	} else {
		num = sscanf(buf, "%ld", &bignumber);
		if (num != 1) {
			kvfree(buf);
			return -EFAULT;
		}
		c = strlen(buf);
		*ppos = c;
		swaphints_page_list[*swaphints_page_offset] = bignumber;
		(*swaphints_page_offset)++;

		if (*swaphints_page_offset >= PGLIST_MAX_SIZE) {
			swapped = 0;
			swapped = swaphints_swap_the_pagelist();
			*swaphints_page_offset = 0;
			if (debug)
				printk(KERN_INFO "Swaphints reclaimed %d pages",
				       swapped);
		}
		kvfree(buf);
		return c;
	}
}

static int show_swaphints(struct seq_file *s, void *p)
{
	seq_printf(s, "swaphints lives here");
	return 0;
}

static int swaphints_open(struct inode *inode, struct file *file)
{
	return single_open(file, show_swaphints, NULL);
}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 8, 0)
static struct proc_ops swaphelper_proc_ops = {
	.proc_read = swaphints_read,
	.proc_write = swaphints_write,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
	.proc_open = swaphints_open,
};
#else
static const struct file_operations swaphelper_proc_ops = {
	.open = swaphints_open,
	.read = swaphints_read,
	.llseek = seq_lseek,
	.release = single_release,
	.write = swaphints_write,
};
#endif

static int __init swaphints_example_init(void)
{
	/* create the /proc file */
	swaphints_proc_file =
		proc_create(PROCFS_NAME, 0666, NULL, &swaphelper_proc_ops);

	if (swaphints_proc_file == NULL) {
		remove_proc_entry(PROCFS_NAME, NULL);
		printk(KERN_ALERT "Error: Could not initialize /proc/%s\n",
		       PROCFS_NAME);
		return -ENOMEM;
	}

	if ((swaphints_page_list =
		     kvcalloc(PGLIST_MAX_SIZE, sizeof(unsigned long),
			      GFP_KERNEL)) == NULL)
		return -ENOMEM;

	if ((swaphints_page_offset =
		     kvzalloc(sizeof(unsigned long), GFP_KERNEL)) == NULL)
		return -ENOMEM;

	(*swaphints_page_offset) = 0;

	printk(KERN_INFO "/proc/%s created, v%s\n", PROCFS_NAME,
	       VERSION_NUMBER);
	return 0; /* everything is ok */
}

static void __exit swaphints_example_exit(void)
{
	remove_proc_entry(PROCFS_NAME, NULL);
	kvfree(swaphints_page_list);
	kvfree(swaphints_page_offset);
	printk(KERN_INFO "Cleaning Up swaphints!\n");
}

module_init(swaphints_example_init);
module_exit(swaphints_example_exit);
MODULE_LICENSE("GPL");
