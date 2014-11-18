#!/bin/bash

#  
# Changes ownership and creates the required symbolic link when
# installing the adhoc-connect package.
#
# Synopsis: ./fix-files-adhoc-connect.sh
#
# Author : Johan Landin <johan.landin@chalmers.se>
# Changed: 2014-11-18

# Define various variables
#
FILENAME=`readlink -f $0`
DIRNAME=`dirname $FILENAME`
PKG=${DIRNAME##/*/}
PKGNAME=${PKG%-*}
PKGVERSION=${PKG##*-}

# Exit if not root
#

die()
{
    echo $1 >&2
    exit 1
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

main()
{
    if [ "$EUID" != "0" ]; then 
        die "Only root should run this, exiting..."
    fi
        
    #
    if ask "Continue and setup $PKGNAME version $PKGVERSION? (y/n): "; then

        echo 'Setting up adhoc-connect ...'
        echo
        
        # Create a symbolic link pointing at the current version
        cd $DIRNAME/.. || die "Cannot change to $PKGNAME top directory"
        rm -f $PKGNAME
        ln -f --symbolic $PKG $PKGNAME || die "Failed to link $PKGNAME to $PKG"
        
        # Fix SELinux context errors
        restorecon -FR $DIRNAME || die "SELinux context on $DIRNAME could not be reset"
        restorecon -F $PKGNAME || die "SELinux context on $PKGNAME could not be reset"
        exit $?

    else
        #
        echo 'No action taken ...'
        echo
        exit 0
        #
    fi
}

main "$@"

#
##[End of File]##
