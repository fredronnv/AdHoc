#!/bin/bash

#
# Installs or upgrades the adhoc-connect package
# Find path of this script. This must be done before any
# directory change in this script.
#
FILENAME=`readlink -f $0`
DIRNAME=`dirname $FILENAME`
TOPDIR=`dirname $DIRNAME`
PKG=${DIRNAME##/*/}
PKGNAME=${PKG%-*}
PKGVERSION=${PKG##*-}


if [ $EUID -ne 0 ]; then
    echo "This script needs to be run as root"
    exit 1
fi

CATALOG_URL="https://utveckling.its.chalmers.se/project/2"
CATALOG_OUTPUT=`mktemp`
available_urls=

die()
{
    echo $i
    exit 1
}

get_available_urls()
{
    # Get the available versions of the package, return a list of urls
    wget --no-check-certificate -O $CATALOG_OUTPUT $CATALOG_URL  >/dev/null 2>&1 || die "Cannot contact $CATALOG_URL"
    urls=`grep "<a href=" $CATALOG_OUTPUT | sed "s/<a href/\\n<a href/g" | \
                sed 's/\"/\"><\/a>\n/2' | grep href | grep $PKGNAME | \
                sed 's/<a href="//' | sed 's?"></a>??' | sort`
    rm -f $CATALOG_OUTPUT
    echo $urls
}

get_available_versions()
{
    # Fetch the available urls and extract the versions of the package
    available_urls=`get_available_urls`
    for v in $available_urls; do
        v1=`echo $v | cut -f2- -d/`
        v2=`basename $v1 .tar`
        ret="$ret $v2"
    done
    echo $ret
}

get_installed_versions()
{
    ls $TOPDIR | grep $PKGNAME- | egrep -v '\.tar.*$'
}

ask() 
{
    # http://djm.me/ask
    while true; do
 
        if [ "${2:-}" = "Y" ]; then
            prompt="Y/n"
            default=Y
        elif [ "${2:-}" = "N" ]; then
            prompt="y/N"
            default=N
        else
            prompt="y/n"
            default=
        fi
 
        # Ask the question
        read -p "$1 [$prompt] " REPLY
 
        # Default?
        if [ -z "$REPLY" ]; then
            REPLY=$default
        fi
 
        # Check if the reply is valid
        case "$REPLY" in
            Y*|y*) return 0 ;;
            N*|n*) return 1 ;;
        esac
 
    done
}

install_cronlink()
{
    rm -f /etc/cron.d/$PKGNAME
    ln -fs $TOPDIR/$PKGNAME /etc/cron.d/$PKGNAME
}

install_version()
{
        echo "Installing $1"
        cd $TOPDIR
        available_urls=`get_available_urls`
        for url in $available_urls; do
            if echo $url | grep $1; then
                dl_url=$url
                break
            fi
        done
        [ -n "$dl_url" ] || die "Cannot find url of $1"
        echo "Downloading from " $dl_url
        wget --no-check-certificate $dl_url >/dev/null 2>&1 || die "Cannot download $dl_url"
        tar xof $1.tar || die "Cannot unpack $1.tar"
        rm -f $PKGNAME || die "Cannot remove activation link $PKGNAME"
        ln -fs $1 $PKGNAME || die "Failed to activate $1"
        rm -f $1.tar
        restorecon -FR `echo $TOPDIR | cut -f-2 -d/`
        restorecon -F $PKGNAME
        cronlink=`readlink /etc/cron.d/$PKGNAME` || install_cronlink
        if [ "$cronlink" != "$TOPDIR/$PKGNAME" ]; then
            install_cronlink
        fi
}

available_versions=`get_available_versions`
installed_versions=`get_installed_versions`
active_version=`readlink $TOPDIR/$PKGNAME`

echo "Available versions:"
echo $available_versions

echo
echo "Locally installed versions:"
for v in $installed_versions; do
    echo $v
done

echo
echo "Active version"
echo $active_version

all_versions=`echo $available_versions $installed_versions $active_version | tr ' ' '\n' | sort -ru`
echo
echo "All versions:"
echo $all_versions

top_version=`echo $all_versions | cut -f1 -d' '`
echo "Top version is $top_version"

if [ "$active_version" == "$top_version" ]; then
    echo "The active version is most recent. No need to upgrade"
    exit 0
elif [ "$active_version" \< "$top_version" ]; then
    if ask "There is a newer version $top_version available, install this?"; then
        install_version $top_version
    fi
fi


##[End of File]##