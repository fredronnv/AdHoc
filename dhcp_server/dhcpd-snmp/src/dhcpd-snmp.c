/* vi: set ts=4 sw=4:
   Copyright (c) 2009-2010 Bernhard Reutner-Fischer
   Licensed under GPL
   See the file COPYING distributed with this package.

   ISC-dhcpd leases. Dump per-pool statistics from lease file
   for retrieval via SNMP.
*/

#define _GNU_SOURCE
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include <features.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <unistd.h>
#include <libgen.h>
#include <ctype.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netdb.h>
#include <errno.h>
#include <string.h>
#include <syslog.h>
#include <getopt.h>
#include <signal.h>
#include <netinet/in.h> /* ntohl() */
#define DEBUG 2
#if defined DEBUG && DEBUG
# include <assert.h>
#else
# define assert(...) /* nothing */
#endif

static char *progname;
#define LEASE_FILE "/var/lib/dhcp/db/dhcpd.leases"
#define BASEOID "1.3.6.1.4.1.21695.1.2"
#define MAX_CACHE_AGE (60*5) /* 5 minutes */
static unsigned int max_cache_age;

static char *lease_file;
typedef struct cfg_entry_t{
	struct cfg_entry_t *next, *prev;
	unsigned int id;
	char *name;
	struct sockaddr *range_start;
	struct sockaddr *range_end;
	time_t *bitmap;
} cfg_entry_t;
/* config-file provided pools */
static cfg_entry_t *cfg;
#define cfg_entry_size (sizeof(cfg_entry_t))

typedef struct lease_entry_t {
	struct lease_entry_t *next, *prev;
	struct in_addr sin_addr;
} lease_entry_t;
#define lease_entry_size (sizeof(lease_entry_t))

typedef struct mib_entry_t {
	struct mib_entry_t *next, *prev;
	int index;
	char *name;
	int total;
	int active;
	int expired;
	int available;
	time_t age;
} mib_entry_t;
#define mib_entry_size (sizeof(mib_entry_t))
typedef enum {
	ENT_IDX = 1, ENT_NAME, ENT_TOTAL,
	ENT_ACTIVE, ENT_EXPIRED, ENT_AVAILABLE, ENT_AGE,
	ENT_LAST} e_mib_entry_t;
static const char *snmp_type_strings[] = {
NULL, /* nil */
"INTEGER",/* index */
"STRING",	/* name */
"INTEGER",/* total */
"INTEGER",/* active */
"INTEGER",/* expired */
"INTEGER",/* available */
"TimeTicks"/* age */
};

typedef struct mib_t {
	unsigned long num_pools;/* total number of configured pools */
	mib_entry_t *entries;/* cache of mib values */
	unsigned long without_pool;/* total number leases outside of confed pools */
} mib_t;
static mib_t *mib;
#define mib_size (sizeof(mib_t))
typedef enum {MIB_POOLCNT = 1, MIB_ENTRIES, MIB_UNPOOLED, MIB_LAST} e_mib_t;

typedef struct {
	e_mib_t mib_p;
	e_mib_entry_t entry_p;
	long idx_p;
} cursor_t;
static cursor_t *_cursor;
#define cursor_size (sizeof(cursor_t))

/* cfg_file for use in child */
static char *cfg_file;

#if defined DEBUG && DEBUG
static int debug = 0;
static void dbg (int lvl, const char *fmt,...)
{
	if (debug >= lvl) {
		char *mess, *vamess;
		va_list arg_ptr;

		va_start(arg_ptr, fmt);
		vasprintf (&vamess, fmt, arg_ptr);
		va_end(arg_ptr);
		asprintf(&mess, "D[%d]: %s", lvl, vamess);
		syslog (LOG_DEBUG, mess);
		free (vamess);
		free (mess);
	}
}
#else
static void dbg (int lvl, const char *s) {}
#endif
static void err (const char *fmt,...)
{
	char *mess, *vamess;
	va_list arg_ptr;
	int errn = errno;

	va_start(arg_ptr, fmt);
	vasprintf (&vamess, fmt, arg_ptr);
	va_end(arg_ptr);

	if (errn)
		asprintf (&mess, "E: %s (%d, %s)", vamess, errn, strerror (errn));
	else
		asprintf (&mess, "E: %s", vamess);
	syslog (LOG_DEBUG|LOG_ERR, mess);
	free (vamess);
	free (mess);
}

static struct sockaddr *string_to_sa (char *host) {
	struct addrinfo hints;
	struct addrinfo *result;
	struct sockaddr *val;
	int ret;

	memset(&hints, 0, sizeof(struct addrinfo));
	hints.ai_family = AF_UNSPEC;
	hints.ai_flags = AI_NUMERICHOST;
	ret = getaddrinfo(host, NULL, &hints, &result);
	if (ret != 0) {
		err (gai_strerror(ret));
		return NULL;
	}
	val = malloc (result->ai_addrlen);
	if (val == NULL) {
		err ("OOM string_to_sa");
		exit (EXIT_FAILURE);
	}
	memcpy (val, result->ai_addr, result->ai_addrlen);
	freeaddrinfo (result);
	return val;
}

static int parse_cfg (const char *cfg_file) {
	int ret = 0;
	unsigned int linenum = 0;
	char *line = NULL;
	size_t line_len = 0;
	FILE *fil = fopen (cfg_file, "r");

	dbg(1, "Parsing cfg_file '%s'", cfg_file);
	if (fil == NULL) {
		err (cfg_file);
		return 1;
	}
	while ((getline (&line, &line_len, fil)) >= 0) {
		char *range_start_str = NULL, *range_end_str = NULL;
		cfg_entry_t *elt;

		++linenum;
		/* leases: /var/lib/dhcpd/dhcpd.leases */
		if (!*line || *line == '#' || *line == '\n'
			|| (sscanf (line, "leases: %as", &lease_file) == 1))
			continue;
		elt = malloc (cfg_entry_size);
		if (elt == NULL) {
			free (line);
			err ("%s:%d: OOM new config-file entry", cfg_file, linenum);
			return 1;
		}
		memset (elt, 0, cfg_entry_size);
		/* pool: 1, u:connect-he, 131.130.240.10-131.130.241.254 */
		if (sscanf (line, "pool: %u, %a[^,], %a[0-9.:a-f]-%a[0-9.:a-f]",
					&elt->id, &elt->name,
					&range_start_str, &range_end_str) != 4) {
			err ("%s:%d: %s", cfg_file, linenum, line);
			free (elt->name);
			free (elt);
			free (range_start_str);
			free (range_end_str);
			ret = 1;
		} else {
			cfg_entry_t *old = cfg;

			elt->range_start = string_to_sa(range_start_str);
			elt->range_end = string_to_sa(range_end_str);
			free (range_start_str);
			free (range_end_str);
			if (old) {
				for (; old->next; old = old->next)
					;
				old->next = elt;
				elt->prev = old;
			} else
				cfg = elt;
		}
	}
	free (line);
	fclose (fil);
	dbg(2, "done (%d)", ret);
	return ret;
}

static void usage (void) {
	fprintf (stderr, "Usage: %s\n"
		"\t-c\tpath/to/%s.conf (default: ./%s.conf)\n"
		"\t-a\tmaximum age for value cache in seconds (default: %d)\n"
#if defined DEBUG && DEBUG
		"\t-d\tincrease debug-level by 1\n"
#endif
		, progname, progname, progname, MAX_CACHE_AGE);
}

#define sa4_to_uint32(sa) \
	(ntohl(((struct sockaddr_in*)sa)->sin_addr.s_addr))

static int ip4_compare(in_addr_t ip, in_addr_t lower, in_addr_t upper)
{
	if (ntohl(ip) < ntohl(lower))
		return -1;
	else if (ntohl(ip) > ntohl(upper))
		return 1;
	return 0;
}

static cfg_entry_t* get_pool_for (struct sockaddr *sa) {
	cfg_entry_t *tmp;
	struct sockaddr_in const *sin;/* *range_start, *range_end;*/

	sin = ((struct sockaddr_in *)sa);

	for (tmp = cfg; tmp; tmp = tmp->next) {
		if (!ip4_compare (sin->sin_addr.s_addr,
						((struct sockaddr_in*)tmp->range_start)->sin_addr.s_addr,
						((struct sockaddr_in*)tmp->range_end)->sin_addr.s_addr))
			return tmp;
	}
	return NULL;
}

#if 0
static cfg_entry_t* get_pool (unsigned int id) {
	cfg_entry_t *tmp;

	for (tmp = cfg; tmp; tmp = tmp->next) {
		if (tmp->id == id)
			return tmp;
	}
	return NULL;
}
#endif

static mib_entry_t* get_mib_entry (int pool_id) {
	mib_entry_t *elt;

	for (elt = mib->entries; elt; elt = elt->next) {
		if (elt->index == pool_id)
			return elt;
	}
	return NULL;
}

static int get_mib_entry_next_id (int old_idx) {
	mib_entry_t *elt = get_mib_entry(old_idx);
	if (!elt || !elt->next)
		return -1;
	return elt->next->index;
}

static void add_mib_entry (mib_entry_t* elt) {
	mib_entry_t *left = NULL, *right = NULL;
	mib_entry_t **ent = &mib->entries;

	while (*ent) {
		if ((*ent)->index < elt->index) {
			if (!left || (*ent)->index > left->index)
				left = *ent;
		}
		if ((*ent)->index > elt->index) {
			if (!right || right->index > (*ent)->index)
				right = *ent;
		}
		*ent = (*ent)->next;
	}
	elt->next = right;
	elt->prev = left;
	if (right)
		right->prev = elt;
	if (left)
		left->next = elt;
	*ent = elt;
	while ((*ent)->prev)
		*ent = (*ent)->prev;
}

static mib_entry_t* get_or_alloc_mib_entry (int pool_id, cfg_entry_t *pool) {

	mib_entry_t *old, *elt;

	old = get_mib_entry (pool_id);
	if (old)
		return old;

	for (old = mib->entries; old; old = old->next) {
		if (old->index > pool_id)
			break;
	}
	/* new entry, sorted by id */
	dbg(3, "new pool %d", pool_id);
	elt = malloc(mib_entry_size);
	if (elt == NULL) {
		err ("OOM mib_entry");
		exit (EXIT_FAILURE);
	}
	memset(elt, 0, mib_entry_size);
	elt->index = pool->id;
	elt->name = pool->name;
	elt->total = 1 +
		sa4_to_uint32(pool->range_end) - sa4_to_uint32(pool->range_start);
	pool->bitmap = realloc(pool->bitmap, elt->total * sizeof(time_t));
	if (pool->bitmap == NULL) {
		err ("OOM mib_entry bitmap");
		exit (EXIT_FAILURE);
	}
	memset(pool->bitmap, 0, elt->total * sizeof(time_t));
	add_mib_entry(elt);
	mib->num_pools++;
	return elt;
}

static bool parse_leases (void) {
	char *old_tz, *line, *lin = NULL;
	size_t line_len;
	FILE *fil;

	time_t now;
	char *tmp1, *tmp2;
	int dummy, tm_sec, tm_min, tm_hour, tm_mday, tm_mon, tm_year;
	enum {START = 0, GOT_LEASE = (1<<0), GOT_ENDTIME = (1<<1), STOP = (1<<2)};
	unsigned int state = START;
	cfg_entry_t *pool = NULL; /* silence gcc */
	mib_entry_t *me = me; /* silence gcc */
	uint32_t ip = 0; /* silence gcc */

	if (lease_file == NULL || (fil = fopen(lease_file, "r")) == NULL)
		return 1;
	tmp1 = malloc (NI_MAXHOST);
	tmp2 = malloc (NI_MAXHOST);
	if (tmp1 == NULL || tmp2 == NULL) {
		err ("OOM parsing leases");
		fclose (fil);
		free (tmp1);
		free (tmp2);
		return 1;
	}
	/* reset stats */
	for (me = mib->entries; me; me = me->next) {
		me->active = 0;
		me->expired = 0;
		me->available = 0;
	}
	/* Have to switch to UTC since leases are stored in that TZ.  */
	old_tz = getenv("TZ");
	setenv("TZ", "", 1);
	tzset();
	now = time(NULL);
	while (getline (&lin, &line_len, fil) >= 0) {
		line = lin;
		while (*line == ' ' || *line == '\t') {
			++line;
			--line_len;
		}
		memset (tmp1, 0, NI_MAXHOST);
		memset (tmp2, 0, NI_MAXHOST);
		if (state == START) {
			pool = NULL;
			me = NULL;
			ip = 0;
		}
		if (sscanf (line, "lease %[0-9.:a-f] {", tmp1) == 1) {
			struct sockaddr *sa = string_to_sa (tmp1);
			pool = get_pool_for (sa);
			if (pool) {
				state |= GOT_LEASE;
				dbg(5, "%s -> pool_id=%d", tmp1, pool->id);
				me = get_or_alloc_mib_entry (pool->id, pool);
				ip = sa4_to_uint32 (sa) - sa4_to_uint32(pool->range_start);
			} else {
				dbg(5, "no pool for %s", tmp1);
				mib->without_pool++;
			}
			free (sa);
		} else if ((state & GOT_LEASE)
					&& strncmp(line, "ends never;", 11) == 0) {
//			state |= GOT_ENDTIME;
			pool->bitmap[ip] = -1;
		} else if ((state & GOT_LEASE)
					/* weekday year/month/day hour:minute:second */
					&& sscanf (line, "ends %d %d/%d/%d %d:%d:%d ;", &dummy,
								&tm_year, &tm_mon, &tm_mday,
								&tm_hour, &tm_min, &tm_sec) == 7) {
			time_t ends;
			struct tm tm;

			memset(&tm, 0, sizeof(tm));
			tm.tm_sec = tm_sec;
			tm.tm_min = tm_min;
			tm.tm_hour = tm_hour;
			tm.tm_mday = tm_mday;
			tm.tm_mon = tm_mon - 1;
			tm.tm_year = tm_year;
			/* tm.tm_isdst = -1; */
			if (tm_year > 1900)
				tm.tm_year -= 1900;
			ends = mktime(&tm);
			if (ends == -1)
				err("mktime");
			/* If it ends and is younger than what we had before, use it.  */
			else if (pool->bitmap[ip] != -1
					&& difftime(pool->bitmap[ip], ends) < (double)0) {
				pool->bitmap[ip] = ends;
//				state |= GOT_ENDTIME;
			}
		} else if (!strncmp(line, "}\n", 2))
			state = START; /* next lease block */
	}
	fclose (fil);
	free (lin);
	free (tmp1);
	free (tmp2);
	for (pool = cfg; pool; pool = pool->next) {
		me = get_mib_entry(pool->id);
		/* If we saw no leases for this pool then we can ignore that
		 * whole MIB entry.  */
		if (!me)
			continue;
		for (ip = 0; (int)ip < me->total; ++ip) {
			time_t ends = pool->bitmap[ip];

			if (ends == -1)
				me->active++;
			else if (ends == 0) ; /* not seen */
			else if (difftime(ends, now) < (double)0)
				me->expired++;
			else
				me->active++;
		}
		memset(pool->bitmap, 0, me->total * sizeof(time_t));
	}
	/* stamp mib entries and update stats */
	for (me = mib->entries; me; me = me->next) {
		me->age = now;
		me->available = me->total - me->active;
	}
	if (old_tz)
		setenv("TZ", old_tz, 1);
	else
		unsetenv("TZ");
	tzset();
	return 0;
}

static cursor_t *cursor_next(cursor_t *c) {
	int minidx = mib->entries->index;

	if (c->mib_p == MIB_ENTRIES) {
		if (c->idx_p < minidx)
			c->idx_p = minidx;
		else
			c->idx_p = get_mib_entry_next_id(c->idx_p);
		if (c->idx_p < minidx || c->entry_p < ENT_IDX) {
			if (++c->entry_p >= ENT_LAST)
				c->mib_p++;
			else
				c->idx_p = minidx;
		}
	} else {
		if (++c->mib_p == MIB_ENTRIES)
			return cursor_next(c);
	}
	if (c->mib_p >= MIB_LAST)
		return NULL;
	return c;
}

static char* snmp_oid(cursor_t *c)
{
	char *ret;

	if (!c)
		return NULL;
	if (c->mib_p == MIB_ENTRIES) {
		if (c->idx_p >= 0)
			asprintf(&ret, BASEOID ".%u.%u.%lu",
					c->mib_p, c->entry_p, (unsigned long)c->idx_p);
		else
			asprintf(&ret, BASEOID ".%u.%u", c->mib_p, c->entry_p);
	} else
		asprintf(&ret, BASEOID ".%d", c->mib_p);
	return ret;
}

static const char* snmp_type(cursor_t *c) {
	if (!c)
		return NULL;
	if (c->mib_p == MIB_POOLCNT)
		return snmp_type_strings[1];
	else if (c->mib_p == MIB_ENTRIES)
		return snmp_type_strings[c->entry_p];
	else if (c->mib_p == MIB_UNPOOLED)
		return snmp_type_strings[1];
	return NULL;
}

static char* snmp_value(cursor_t *c)
{
	char *ret = NULL;
	time_t now;

	if (!c)
		return NULL;
	now = time(NULL);
	if (difftime(now, mib->entries->age) > (double)max_cache_age) {
		unsigned short retries = 7;
		unsigned short attempts = 0;

		while (retries--) {
			struct timespec ts, rem;

			ts.tv_sec = 1;
			ts.tv_nsec = 0;
			if (parse_leases())
				attempts++;
			else
				break;
			while (1) {
				if (nanosleep(&ts, &rem) && errno == EINTR)
					memcpy(&ts, &rem, sizeof(struct timespec));
				else
					break;
			}
		}
		if (attempts)
			dbg(0, "%s: %d attempts to parse leases",
				retries ? "WARNING" : "CRITICAL", attempts);
	}
	if (c->mib_p == MIB_POOLCNT)
		asprintf(&ret, "%lu", mib->num_pools);
	else if (c->mib_p == MIB_UNPOOLED)
		asprintf(&ret, "%lu", mib->without_pool);
	else if (c->mib_p == MIB_ENTRIES) {
		mib_entry_t * pool = get_mib_entry(c->idx_p);
		if (pool) {
			switch (c->entry_p) {
				case ENT_IDX: asprintf(&ret, "%u", pool->index); break;
				case ENT_TOTAL: asprintf(&ret, "%u", pool->total); break;
				case ENT_ACTIVE: asprintf(&ret, "%u", pool->active); break;
				case ENT_EXPIRED: asprintf(&ret, "%u", pool->expired); break;
				case ENT_AVAILABLE: asprintf(&ret, "%u", pool->available); break;
				case ENT_NAME: asprintf(&ret, "%s", pool->name); break;
				case ENT_AGE: asprintf(&ret, "%lu",
									(unsigned long)difftime(now,pool->age));
					break;
				default:
					return ret;
			}
		}
	}
	return ret;
}

static char* snmp_response(cursor_t *c, int*error) {
	char *resp = NULL;
	char *oid = snmp_oid(c);
	const char *type = snmp_type(c);
	char *value = snmp_value(c);

	if (oid && type && value)
			asprintf(&resp, "%s\n%s\n%s\n", oid, type, value);
	free(oid);
	free(value);
	*error = resp == NULL;
	return resp == NULL ? "NONE\n" : resp;
}


enum {
	WANT_HANDSHAKE = 0,
	DID_PING = (1<<0),
	WANT_GET = (1<<1),
	WANT_GETNEXT = (1<<2),
	WANT_GETBULK = (1<<3),
	GOT_OID = (1<<4)
};
int main (int argc, char **argv) {
	int opt, ret = EXIT_SUCCESS;
	unsigned state = WANT_HANDSHAKE;

	progname = basename (argv[0]);
	openlog (progname, LOG_PID|LOG_ODELAY, LOG_DAEMON);
	if (setvbuf(stdin, NULL, _IONBF, 0) ||
		setvbuf(stdout, NULL, _IONBF, 0) ||
		setvbuf(stderr, NULL, _IONBF, 0)) {
		err ("failed setting unbuffered I/O!");
		fflush(NULL);
	}
	max_cache_age = MAX_CACHE_AGE;
	while ((opt = getopt (argc, argv,
#if defined DEBUG && DEBUG
							"d"
#endif
							"f:c:a:")) >= 0) {
		switch (opt) {
		case 'c': cfg_file = strdup (optarg); break;
		case 'a': max_cache_age = atoi (optarg); break;
#if defined DEBUG && DEBUG
		case 'd': ++debug; break;
#endif
		default: dbg(2, "Printing help, exit.");
				usage(); closelog (); exit (EXIT_SUCCESS); break;
		}
	}
#if defined DEBUG && DEBUG
	for (opt=0; opt <= argc; ++opt)
		dbg(1, "argv[%d]='%s'", opt, argv[opt]);
#endif
	if (cfg_file == NULL)
		asprintf (&cfg_file, "./%s.conf", progname);
	if (parse_cfg (cfg_file)) {
		err ("Unable to parse cfg file");
		ret = EXIT_FAILURE;
		goto out_cfg_file;
	}
	mib = malloc(mib_size);
	if (mib == NULL) {
		err ("OOM mib");
		ret = EXIT_FAILURE;
		goto out;
	}
	memset(mib, 0, mib_size);

	if (lease_file == NULL)
		lease_file = strdup (LEASE_FILE);
	if (parse_leases ()) {
		err ("Unable to parse leases");
		ret = EXIT_FAILURE;
		goto out;
	}
	dbg (1, "ready to serve requests");
	while (1) {
		int matches = -1;
		char *oid = oid; /* silence gcc */
		char *cmd = NULL;
		size_t cmd_len = 0, oid_len;
		cursor_t c;

		if (getline (&cmd, &cmd_len, stdin) < 0) {
			if (feof(stdin)) {
				dbg(1, "was asked to quit");
				free (cmd);
				goto out;
			}
			err ("getline, %d: %s", errno, strerror(errno));
			continue;
		} else {
			char *tmp = memchr (cmd, '\n', cmd_len);
			cmd[tmp - cmd] = '\0';
		}
		dbg (2, "cmd='%s'", cmd);
		if (state & DID_PING) {
			if (state & (WANT_GETBULK | WANT_GETNEXT | WANT_GET)) {
				oid = cmd;
				while (*oid == ' ' || *oid == '\t' || *oid == '.')
					++oid;
				oid_len = strlen(BASEOID);
				if (memcmp (BASEOID, oid, oid_len) == 0) {
					oid += oid_len;
					oid_len = strlen(oid);
					while (*oid && *oid == '.')
						++oid, --oid_len;
					if (oid)
						state |= GOT_OID;
				}
			} else if (memcmp ("getbulk", cmd, 7) == 0)
				state |= WANT_GETBULK;
			else if (memcmp ("getnext", cmd, 7) == 0)
				state |= WANT_GETNEXT;
			else if (memcmp ("get", cmd, 3) == 0)
				state |= WANT_GET;
			else
				state = WANT_HANDSHAKE;
		} else {
			if (memcmp ("PING", cmd, 4) == 0) {
				printf("PONG\n");
				fflush(stdout);
				state |= DID_PING;
			}
		}
		if (state & GOT_OID) {
			unsigned int dummy;

			memset(&c, 0, sizeof(c));
			if (*oid)
				matches = sscanf(oid, "%u.%u.%lu.%u",
								&c.mib_p, &c.entry_p, (unsigned long*)&c.idx_p,
								&dummy);
			else /* it's just the base oid */
				matches = 0;
			if (matches > 3) /* got nonsense OID */
				c.mib_p = MIB_LAST;
		}
		if ((state & GOT_OID) && matches >= 0) {
			char *response;
			int err;

			if (state & WANT_GETBULK) {
				bool fixup_first = 1;
				do {
					_cursor = &c;
					response = snmp_response(_cursor, &err);
					if (fixup_first-- && err) {
						err = 0;
						_cursor = cursor_next(&c);
						continue;
					} else {
						dbg(2, "response (%s): %s", err?"ERROR":"ok", response);
						printf("%s", response);
						fflush(stdout);
						free(response);
					}
					_cursor = cursor_next(&c);
				} while (!err);
				state = WANT_HANDSHAKE;
			} else {
				if (state & WANT_GETNEXT)
					_cursor = cursor_next(&c);
				else if (state & WANT_GET)
					_cursor = &c;
				dbg(4, "Cursor{%i} = %u.%i.%li",
					matches, c.mib_p, c.entry_p, c.idx_p);
				response = snmp_response(_cursor, &err);
				dbg(2, "response (%s): %s", err?"ERROR":"ok", response);
				printf("%s", response);
				fflush(stdout);
				if (!err)
					free(response);
				state = WANT_HANDSHAKE;
			}
		}
		free (cmd);
		cmd = NULL;
	}
 out:
 out_cfg_file:
	free (cfg_file);
	free (lease_file);
	dbg (1, "exiting");
	{
		cfg_entry_t *xxx;
		while ((xxx = cfg)) {
			cfg = cfg->next;
			free (xxx->bitmap);
			free (xxx->name);
			free (xxx->range_start);
			free (xxx->range_end);
			free (xxx);
		}
	}
	if (mib) {
		mib_entry_t *xxx;
		while ((xxx = mib->entries)) {
			mib->entries = mib->entries->next;
			free (xxx);
		}
		free(mib);
	}
	closelog ();
	return ret;
}
