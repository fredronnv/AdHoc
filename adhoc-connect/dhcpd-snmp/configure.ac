AC_PREREQ(2.57)
AC_INIT([dhcpd_snmp],[1.1.15],[])
AC_CONFIG_SRCDIR([src/dhcpd-snmp.c])
AC_CONFIG_AUX_DIR([config])
AM_CONFIG_HEADER([config.h])
AC_LANG_C
AC_CANONICAL_HOST
AM_INIT_AUTOMAKE([no-dist-gzip dist-bzip2 tar-pax])
dnl AC_PROG_LIBTOOL
AC_PROG_INSTALL
AC_CHECK_TOOL([STRIP],[strip])
ISODATE=`date +%Y-%m-%d`
AC_SUBST(ISODATE)
AC_SUBST(VERSION)
AM_MAINTAINER_MODE
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_ARG_WITH(extra-cflags,
 [  --with-extra-cflags     pass extra cflags to $CC],
 [EXTRA_CFLAGS="$withval"],[EXTRA_CFLAGS=""])

AC_PROG_CC
AC_LANG_PUSH(C)
AC_TRY_COMPILE([],[],[true],
 [AC_MSG_FAILURE([Failed to compile using bare $CC $CFLAGS])])
AC_MSG_CHECKING([which extra cflags to use])
# Remove the -O2:
CFLAGS=`echo $CFLAGS | sed "s/-O[[s0-9]]* *//" `
ac_save_CFLAGS="$CFLAGS"
CFLAGS="$CFLAGS $EXTRA_CFLAGS"
AC_TRY_COMPILE([],[],[true],
 [AC_MSG_FAILURE([Failed to compile using extra cflags for $CC $CFLAGS])])
if test "x$EXTRA_CFLAGS" = "x"; then
  AC_MSG_RESULT([none])
else
  AC_MSG_RESULT([$EXTRA_CFLAGS])
fi
AC_SUBST([EXTRA_CFLAGS])
AC_SUBST(CFLAGS)

AC_PROG_CC_C_O
AC_C_CONST
AC_STRUCT_TM
AC_TYPE_SIZE_T
AC_HEADER_STDC
AC_HEADER_STDBOOL
AC_CHECK_HEADERS([\
features.h \
limits.h \
stdbool.h \
stdio.h \
stdlib.h \
stdarg.h \
unistd.h \
libgen.h \
ctype.h \
time.h \
sys/types.h \
sys/stat.h \
fcntl.h \
sys/socket.h \
netdb.h \
errno.h \
string.h \
syslog.h \
getopt.h \
signal.h \
netinet/in.h \
])
# Check for library functions.
AC_FUNC_MALLOC
AC_FUNC_MEMCMP
AC_CHECK_FUNCS([\
asprintf \
atoi \
closelog \
difftime \
exit \
fclose \
feof \
fflush \
fopen \
fprintf \
free \
freeaddrinfo \
gai_strerror \
getaddrinfo \
getenv \
getline \
getopt \
malloc \
memchr \
memcmp \
memcpy \
memset \
mktime \
nanosleep \
ntohl \
openlog \
printf \
realloc \
setenv \
setvbuf \
sscanf \
strdup \
strerror \
strlen \
strncmp \
syslog \
time \
tzset \
unsetenv \
vasprintf \
])
AC_LANG_POP(C)

AC_CONFIG_FILES([Makefile
src/Makefile
mibs/Makefile
dhcpd_snmp.spec
dhcpd_snmp.lsm
])
AC_OUTPUT
