#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc import *
import uuid
import hashlib
from __builtin__ import classmethod

            
class UserAuthenticationManager(AuthenticationManager):
    manages = None
    
    @classmethod
    def pwhash(cls, cleartext):
        salt = uuid.uuid4().hex
        pw_hash = hashlib.sha256(salt.encode() + cleartext.encode()).hexdigest() + ':' + salt
        return pw_hash
    
    @classmethod
    def check_pw(cls, pw_hash, cleartext):
        password, salt = pw_hash.split(':')
        return password == hashlib.sha256(salt.encode() + cleartext.encode()).hexdigest()
        
    def login(self, session, username, password, generic_password):
        
        if generic_password and password==generic_password:
            session.set("authuser", username)
            return
        if self.server.config("SUPERUSER_PASSWORD", default=None):
            if username == '#root#' and password == self.server.config("SUPERUSER_PASSWORD"):
                session.set("authuser", "#root#")
                return
        try:
            user = self.server.user_manager.get_user(username)
        except LookupError:  # Hide the lookup error, don't give clues as to what was wrong
            raise exterror.ExtAuthenticationFailedError() 
        if self.check_pw(user.password, password):
            session.set("authuser", username)
        else:
            raise exterror.ExtAuthenticationFailedError()

    def logout(self, session):
        session.unset("authuser")

