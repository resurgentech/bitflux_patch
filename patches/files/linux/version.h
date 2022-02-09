//CLEAN_IFDEFS__TOGGLE
/*
mocks to help with removing ifdefs
*/
#define KERNEL_VERSION(a,b,c) (((a) << 16) + ((b) << 8) + ((c) > 255 ? 255 : (c)))
//#define LINUX_VERSION_CODE KERNEL_VERSION(LINUX_VERSION_MAJOR,LINUX_VERSION_SUBLEVEL,LINUX_VERSION_PATCHLEVEL)
#define LINUX_VERSION_CODE (((LINUX_VERSION_MAJOR) << 16) + ((LINUX_VERSION_SUBLEVEL) << 8) + ((LINUX_VERSION_PATCHLEVEL) > 255 ? 255 : (LINUX_VERSION_PATCHLEVEL)))

#define WB_REASON_VMSCAN 0
#define GFP_KERNEL 0
#define PAGEOUTRUN 0
#define DEF_PRIORITY 0
#define true 0
#define false 0
#define NULL 0

#define u8 int
#define bool int
#define MAX_NR_ZONES 200
#define LIST_HEAD(a) struct list_head a
#define INIT_LIST_HEAD(a)
#define unlikely(a) a

struct reclaim_state {
	unsigned long reclaimed_slab;
};

struct scan_control {
	int gfp_mask;
	int order;
	int may_unmap;
	int reclaim_idx;
	int may_writepage;
	int may_swap;
	int nr_scanned;
	int priority;
	struct reclaim_state reclaim_state;
};

struct reclaim_stat {
	unsigned nr_dirty;
};

typedef struct spinlock {
u8 __padding;
} spinlock_t;

struct task_struct {};

struct lruvec {
	spinlock_t lru_lock;
};

struct list_head {
	u8 __padding;
};

struct page { struct list_head lru; };

typedef struct pglist_data {
	spinlock_t lru_lock;
} pg_data_t;

enum lru_list {
	ZONE_HIGHMEM = 0,
};

enum zone_type {
	ZONE_HIGHMEMB = 0,
};

struct mem_cgroup {int swappiness;};

struct lruvec * mem_cgroup_page_lruvec(struct page *page, pg_data_t *pgdat) { return NULL; }
enum lru_list page_lru(struct page *page) { return 0; }
enum zone_type page_zonenum(struct page *page) { return 0; }
void list_move(struct list_head *lru, struct list_head *head) { return; }
void update_lru_sizes(struct lruvec *lruvec, enum lru_list a, long unsigned int *b) { return; }
unsigned long shrink_page_list(struct list_head *head, pg_data_t *pgdat, struct scan_control *sc, int a, struct reclaim_stat *dummy_stat, bool b) { return 0; }
void move_pages_to_lru(struct lruvec *lruvec, struct list_head *head) { return; }
int list_empty(const struct list_head *head) { return 0; }
struct page * lru_to_page(const struct list_head *head) { return NULL; }
void list_del(struct list_head * lru) { return; }

void age_active_anon(pg_data_t *pgdat, struct scan_control *sc) { return; }
void snapshot_refaults(struct mem_cgroup *target_memcg, pg_data_t *pgdat) { return; }
void set_task_reclaim_state(struct task_struct *task, struct reclaim_state *rs) { return; }

void putback_lru_page(struct page *page) { return; }
void spin_unlock_irq(spinlock_t *lru_lock) { return; }
void spin_lock_irq(spinlock_t *lru_lock) { return; }
void wakeup_flusher_threads(int a) { return; }
void __fs_reclaim_acquire(void) { return; }
void fs_reclaim_acquire(int a) { return; }
void count_vm_event(int a) { return; }
void __fs_reclaim_release(void) { return; }
void fs_reclaim_release(int a) { return; }
pg_data_t * page_pgdat(struct page *page) { return NULL; }
unsigned long compound_nr(struct page *page) { return 0; }
int PageHead(struct page *page) { return 0; }
unsigned long compound_order(struct page *page) { return 0; }
int list_is_singular(struct list_head *a) { return 0;}
int __isolate_lru_page_prepare(struct page *page, int b) { return 0; }
int get_page_unless_zero(struct page *page) { return 0; }
int TestClearPageLRU(struct page *page) { return 0; }
void put_page(struct page *page) { return; }
int __isolate_lru_page(struct page *page, int b) { return 0; }
void ClearPageActive(struct page *page) { return; }

#define EXPORT_SYMBOL(a)
//CLEAN_IFDEFS__TOGGLE