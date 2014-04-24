#!/bin/sh
set -x
[ -d config ] || mkdir config
${ACLOCAL-aclocal} -I config &&
#${LIBTOOLIZE-libtoolize} --force --copy &&
${AUTOHEADER-autoheader} &&
${AUTOMAKE-automake} --foreign --add-missing --copy &&
${AUTOCONF-autoconf} &&
echo "OK."
ret=$?
if test $ret -ne 0
then
  echo "got error ($ret)."
fi
rm -rf autom4te.cache
exit $ret
