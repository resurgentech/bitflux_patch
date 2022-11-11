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
#include <linux/slab.h>


MODULE_DESCRIPTION("Proc File Enabled Swap Hint Handler.");
#define VERSION_NUMBER "0.64"
MODULE_VERSION(VERSION_NUMBER);
#define PROCFS_NAME "swaphints"


/**
 * Internal error codes for debug and feedback
 */
#define ERR_SWAPHINTS_ISOLATE_LRU EINVAL
#define ERR_SWAPHINTS_UNEVICTABLE EPERM

/**
 * Structure to hold return values from reclaim_page()
 */
struct swaphints_status_struct {
	u64 *pfns;
	u32 *status;
	u32 *retries;
	int head;
	int tail;
	int max;
};

/**
 * Structure used with proc iterators
 */
struct swaphints_status_entry {
	u64 pfn;
	u32 status;
	u32 retries;
};

static DEFINE_MUTEX(swaphints_lock);

/**
 * Structure holds list of pfns to swap and a buffer for write
 */
struct swaphints_pfn_list_struct {
	u64 *pfns;
	char *buffer;
	int index;
	int max;
	int wake_limit;
};

/**
 * Returns the number of empty entries in the ring buffer
 */
#define swaphints_status_buffer_space(b) \
	(((b).tail == (b).head) ? \
		((b).max) : \
		(((b).tail > (b).head) ? \
			(((b).tail - (b).head - 1) & ((b).max)) : \
			((b).max + (b).tail - (b).head) \
		) \
	)
/**
 * Returns true if buffer is empty
 */
#define swaphints_status_buffer_empty(b)    ((b).head == (b).tail)

/**
 * This structure hold information about the /proc file
 */
static struct proc_dir_entry *swaphints_proc_file;

/**
 * ring buffer for return valus from swaphints_swap_a_page
 * data is fed back to userspace to improve accuracy
 */
struct swaphints_status_struct status_buffer;

/**
 * list of pfns userspace requesting to be reclaimed
 */
struct swaphints_pfn_list_struct swaphints_pfn_list;


/* Module Parameters */

/**
 * Flags debug printf's when set to 1
 */
int debug = 0;
module_param(debug, int, 0660);

/**
 * write buffer for user space to send via /proc/swaphints
 */
int write_buffer_size = 1024;
module_param(write_buffer_size, int, 0660);

/**
 * Length of pfn list buffer to stash user input into
 */
int pfn_list_length = 1<<20;
module_param(pfn_list_length, int, 0660);

/**
 * How many pfns to swap out before waking reclaim walk up
 */
int pfn_list_wake_limit = 512;
module_param(pfn_list_wake_limit, int, 0660);

/**
 * Length of ring buffer for stashing status of pfn
 * MUST BE power of 2 or the math doesn't work in our buffer logic.
 */
int status_max_len = 1<<21;
module_param(status_max_len, int, 0660);

/**
 * Length of ring buffer for stashing status of pfn
 * MUST BE power of 2 or the math doesn't work in our buffer logic.
 */
int reclaim_retries = 12;
module_param(reclaim_retries, int, 0660);

/**
 * Internal Function to request the reclamation of a single specific page.
 */
static unsigned long swaphints_swap_a_page(unsigned long pagenumber)
{
	struct page *page;
	u64 pfn = pagenumber;

	page = pfn_to_page(pfn);

	ClearPageReferenced(page);
	test_and_clear_page_young(page);
	return reclaim_page(page);
}

/**
 * Add status of pfn reclaim to ring buffer
 */
static void swaphints_push_status(u32 status, u32 retries, u64 pfn)
{
	int next_head;
	status_buffer.pfns[status_buffer.head] = pfn;
	status_buffer.status[status_buffer.head] = status;
	status_buffer.retries[status_buffer.head] = retries;
	/**
	 *  If head is already at end of buffer
	 *  Then we are going to wrap back to zero otherwise increment
	 */
	if (status_buffer.head == status_buffer.max)
		next_head = 0;
	else
		next_head = status_buffer.head + 1;

	/**
	 * If buffer is full we need to advance the tail.
	 * If the tail is at the end of the buffer we wrap it.
	 */
	if (swaphints_status_buffer_space(status_buffer) == 0) {
		if (status_buffer.tail == status_buffer.max)
			status_buffer.tail = 0;
		else
			status_buffer.tail++;
	}
	status_buffer.head = next_head;
}

/**
 * Remove status from ring buffer
 */
static int swaphints_pop_status(u32 *status, u32 *retries, u64 *pfn)
{
	/**
	 * Nothing if return if we're empty
	 */
	if (swaphints_status_buffer_empty(status_buffer))
		return 1;
	*pfn = status_buffer.pfns[status_buffer.tail];
	*status = status_buffer.status[status_buffer.tail];
	*retries = status_buffer.retries[status_buffer.tail];

	/**
	 * If the tail is at the end of the buffer we wrap it.
	 */
	if (status_buffer.tail == status_buffer.max)
		status_buffer.tail = 0;
	else
		status_buffer.tail++;

	return 0;
}

/**
 * Internal function to process a list of specific pages through individual
 * reclamation.
 *
 * We also proactively wakeup the flusher thread.  We believe this improves
 * long term performance, keeps memory from being filled with reclaim pages,
 * and prevents the flusher from hitting a state where it will have to stop 
 * to reclaim in a more aggressive manner.
 */
static int swaphints_swap_the_pagelist(void)
{
	int pages_swapped = 0;
	int i;
	int j;
	unsigned long status;
	u64 pfn;

	/**
	 * Loop through pfn list to target each pfn
	 */
	for (i = 0; i < swaphints_pfn_list.index; i++) {
		pfn = swaphints_pfn_list.pfns[i];
		for (j = 0; j < reclaim_retries; j++) {
			status = swaphints_swap_a_page(pfn);
			if (status != 0)
				break;
		}
		/**
		 * Log status of each swap
		 */
		swaphints_push_status(status, j, pfn);
		/**
		 * Status of >0 means we successfull swapped
		 */
		if (status > 0)
			pages_swapped += status;
		/**
		 * Every few hundred pages we proactively wakeup the flusher.
		 */
		if ((i % swaphints_pfn_list.wake_limit) == 0)
			request_reclaim_flusher_wakeup();
	}
	/**
	 * Wakeup flusher thread
	 */
	request_reclaim_flusher_wakeup();
	swaphints_pfn_list.index = 0;
	return pages_swapped;
}

static void swaphints_swapnow(void)
{
	int swapped;
	if (debug)
		printk(KERN_INFO "Beginning swap attempt of %d pages\n", swaphints_pfn_list.index);
	if (swaphints_pfn_list.index > 0)
		swapped = swaphints_swap_the_pagelist();
	if (debug)
		printk(KERN_INFO "Swaphints reclaimed %d pages\n", swapped);
}

/**
 * This function is called with the /proc file is written
 * It accepts either a pfn in the form of a numeric decimal string (e.g.
 * "437895468") or the key word "swapnow" all other inputs are ignored.
 * subsequent numbers submitted are added to a list, and
 * "swapnow" will begin processing the list.
 */
static ssize_t swaphints_write(struct file *file, const char __user *ubuf,
			       size_t count, loff_t *ppos)
{
	unsigned long pfn;
	int ret = 0;

	/**
	 * We're going to ignore write that too long or continued.
	 */
	if (*ppos > 0 || count > swaphints_pfn_list.max) {
		printk(KERN_INFO "Swaphints write hit too long");
		printk(KERN_INFO "");
		return -EFAULT;
	}

	mutex_lock(&swaphints_lock);

	/**
	 * Copy data from userspace to a buffer we can use here.
	 */
	if (copy_from_user(swaphints_pfn_list.buffer, ubuf, count)) {
		printk(KERN_INFO "Swaphints copy_from_user failed\n");
		ret = -EFAULT;
		goto write_exit;
	}

	/**
	 * If we recieve swapnow we're just going to swap whats in the list
	 */
	if (strstr(swaphints_pfn_list.buffer, "swapnow")) {
		swaphints_swapnow();
	} else {
		/**
		 * Find the pfn from userspace and record if valid
		 */
		if (sscanf(swaphints_pfn_list.buffer, "%ld", &pfn) != 1) {
			printk(KERN_INFO "Swaphints can't read number '%s'\n", swaphints_pfn_list.buffer);
			ret = -EFAULT;
			goto write_exit;
		}
		if (pfn == 0) {
			printk(KERN_INFO "Swaphints recieved pfn 0\n");
			ret = -EFAULT;
			goto write_exit;
		}
		swaphints_pfn_list.pfns[swaphints_pfn_list.index] = (u64) pfn;
		swaphints_pfn_list.index++;

		/**
		 * If our list is full, we swap now.
		 */
		if (swaphints_pfn_list.index == (swaphints_pfn_list.max - 1))
			swaphints_swapnow();
	}
	ret = strnlen(swaphints_pfn_list.buffer, write_buffer_size);
	*ppos = ret;
	memset((void *)swaphints_pfn_list.buffer, 0, write_buffer_size);
write_exit:
	mutex_unlock(&swaphints_lock);
	return ret;
}

/* Iterators for procfile reads */

/**
 * Start of iteration.  Returns NULL if there is nothing to do.
 * Or passes the first object to the _show() function.
 */
static void *swaphints_start(struct seq_file *swaphint, loff_t *pos)
{
	struct swaphints_status_entry *s;

	s = kvzalloc(sizeof(*s), GFP_KERNEL);

	mutex_lock(&swaphints_lock);

	if (swaphints_pop_status(&(s->status), &(s->retries), &(s->pfn))) {
		kvfree(s);
		return NULL;
	}

	return s;
}

/**
 * Next iter.  Also returns NULL if there is nothing to do.
 * Or passes the first object to the _show() function.
 */
static void *swaphints_next(struct seq_file *swaphint, void *v, loff_t *pos)
{
	struct swaphints_status_entry *s = v;

	++(*pos);

	if (swaphints_pop_status(&(s->status), &(s->retries), &(s->pfn))) {
		kvfree(s);
		return NULL;
	}

	return s;
}

/**
 * End of iteration.  Called if _start() or _next() returns NULL.
 */
static void swaphints_stop(struct seq_file *swaphint, void *v)
{
	mutex_unlock(&swaphints_lock);
}

/**
 * 'print' data to userspace.  Passes data upstream for sending back to user.
 */
static int swaphints_show(struct seq_file *swaphint, void *v)
{
	struct swaphints_status_entry *s = v;

	if (seq_write(swaphint, &(s->status), sizeof(s->status)))
		return -1;
	if (seq_write(swaphint, &(s->retries), sizeof(s->retries)))
		return -1;
	if (seq_write(swaphint, &(s->pfn), sizeof(s->pfn)))
		return -1;

	return 0;
}

static const struct seq_operations swaphelper_op = {
	.start =	swaphints_start,
	.next =		swaphints_next,
	.stop =		swaphints_stop,
	.show =		swaphints_show
};

/**
 * Called when user does open() to file, for read or write.
 * Note it sets us up to use the seq_ iterators.
 */
static int swaphints_open(struct inode *inode, struct file *file)
{
	int ret;

	ret = seq_open(file, &swaphelper_op);
	if (ret)
		return ret;

	return 0;
}

static const struct proc_ops swaphints_proc_ops = {
	.proc_open	= swaphints_open,
	.proc_read	= seq_read,
	.proc_write	= swaphints_write,
	.proc_lseek	= seq_lseek,
	.proc_release	= seq_release,
};

/**
 * Clean up module buffers
 */
static void swaphints_cleanup(void)
{
	kvfree(swaphints_pfn_list.pfns);
	kvfree(swaphints_pfn_list.buffer);
	kvfree(status_buffer.pfns);
	kvfree(status_buffer.status);
	kvfree(status_buffer.retries);
}

static int __init swaphints_init(void)
{
	/* create the /proc file */
	swaphints_proc_file =
		proc_create(PROCFS_NAME, 0666, NULL, &swaphints_proc_ops);
	if (!swaphints_proc_file) {
		remove_proc_entry(PROCFS_NAME, NULL);
		printk(KERN_ALERT "Error: Could not initialize /proc/%s\n",
		       PROCFS_NAME);
		return -ENOMEM;
	}

	/**
	 * Need to check the status_max_len to valid it's a power of two.
	 */
	if ((status_max_len < 4) || \
	    (status_max_len & (status_max_len - 1))) {
		printk(KERN_INFO "/proc/%s failed, status_max_len=%d should be power of two\n",PROCFS_NAME,status_max_len);
		return -EINVAL;
	}

	/**
	 * Tedious initialization of module scope structures
	 */
	swaphints_pfn_list.index = 0;
	swaphints_pfn_list.max = pfn_list_length;
	swaphints_pfn_list.wake_limit = pfn_list_wake_limit;
	if (!(swaphints_pfn_list.pfns = kvcalloc(swaphints_pfn_list.max, sizeof(*swaphints_pfn_list.pfns), GFP_KERNEL))) {
		swaphints_cleanup();
		return -ENOMEM;
	}
	if (!(swaphints_pfn_list.buffer = kvzalloc(write_buffer_size, GFP_KERNEL))) {
		swaphints_cleanup();
		return -ENOMEM;
	}
	status_buffer.head = 0;
	status_buffer.tail = 0;
	status_buffer.max = status_max_len - 1;
	if (!(status_buffer.pfns = kvcalloc(status_buffer.max + 1, sizeof(*status_buffer.pfns), GFP_KERNEL))) {
		swaphints_cleanup();
		return -ENOMEM;
	}
	if (!(status_buffer.status = kvcalloc(status_buffer.max + 1, sizeof(*status_buffer.status), GFP_KERNEL))) {
		swaphints_cleanup();
		return -ENOMEM;
	}
	if (!(status_buffer.retries = kvcalloc(status_buffer.max + 1, sizeof(*status_buffer.retries), GFP_KERNEL))) {
		swaphints_cleanup();
		return -ENOMEM;
	}

	printk(KERN_INFO "/proc/%s created, v%s\n", PROCFS_NAME,
	       VERSION_NUMBER);
	return 0;
}

static void __exit swaphints_exit(void)
{
	remove_proc_entry(PROCFS_NAME, NULL);
	swaphints_cleanup();
	printk(KERN_INFO "Cleaning Up swaphints!\n");
}

module_init(swaphints_init);
module_exit(swaphints_exit);
MODULE_LICENSE("GPL");
