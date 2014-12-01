#!/bin/bash

# Changes ownership and creates the required symbolic link when
# installing the adhoc-server package.
#
# Synopsis: ./fix-files-adhoc-server.sh
#
# Author : Johan Landin <johan.landin@chalmers.se>
# Changed: 2014-11-20

# Define various variables
#
FILENAME=`readlink -f $0`
DIRNAME=`dirname $FILENAME`
PKG=${DIRNAME##/*/}
PKGNAME=${PKG%-*}
PKGVERSION=${PKG##*-}

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

    if ask "Continue and setup $PKGNAME version $PKGVERSION?: "; then

       echo "Setting up $PKGNAME ..."
       echo
        
       # Change ownership of all files in the current version
       chown -Rh srvadhoc:srvadhoc $DIRNAME
        
       # Create a symbolic link pointing at the current version
       cd $DIRNAME/.. || die "Cannot change to $PKGNAME top directory"
       rm -f $PKGNAME
       ln -f --symbolic $PKG $PKGNAME || die "Failed to link $PKGNAME to $PKG"
       chown -h srvadhoc:srvadhoc $PKGNAME || die "Could not change ownership of files in $PKG"
           
    else
        echo 'No action taken ...'
        echo
        exit 0
    fi
}

main "$@"

#
##[End of File]##