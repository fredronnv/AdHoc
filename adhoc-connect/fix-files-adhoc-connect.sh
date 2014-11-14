#!/bin/bash

#  
# Changes ownership and creates the required symbolic link when
# installing the adhoc-connect package.
#
# Synopsis: ./fix-files-adhoc-connect.sh
#
# Author : Johan Landin <johan.landin@chalmers.se>
# Changed: 2014-11-13

# Define various variables
#
FILENAME=`readlink -f $0`
DIRNAME=`dirname $FILENAME`
PKG=${DIRNAME##/*/}
PKGNAME=${PKG%-*}
PKGVERSION=${PKG##*-}

# Exit if not root
#
if [ "$EUID" != "0" ]
then
        echo "Only root should run this, exiting..."
        exit
fi

#
# The real work begins here...
#

# Ask for confirmation
#
echo ' '
echo -n "Continue and setup $PKGNAME version $PKGVERSION? (y/n): "
read YESNO
echo ' '

# If the answer was [y|Y], proceed and setup adhoc-connect
#
if [ \( "$YESNO" = "y" \) -o \( "$YESNO" = "Y" \) ]
then
   #
   echo 'Setting up adhoc-connect ...'
   echo ' '

   # Change ownership of all files in current version
   #
   chown -Rh root:root $DIRNAME

   # Create a symbolic link pointing at the current version
   #
   cd $DIRNAME
   cd ..
   rm -f $PKGNAME
   ln -f --symbolic $PKG $PKGNAME

   # Fix SELinux context errors
   #
   restorecon -FR $DIRNAME
   restorecon -F $PKGNAME

   #
else
   #
   echo 'No action taken ...'
   echo ' '
   #
fi

#
##[End of File]##
