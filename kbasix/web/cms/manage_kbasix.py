"""
KBasix management module for the KBasix CMS.
Created by: Pamela Brittain
            James Colliander
            Marco De la Cruz-Heredia
            Emile LeBlanc
Coded by: Marco De la Cruz-Heredia (marco@math.utoronto.ca)

Copyright (c) 2012, Department of Mathematics, University of Toronto
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

_VERSION = 0.10

import time
import os
import hashlib
import fnmatch
from manage_users import _read_file, _save_file, _info
from defs import kbasix


class CreateTokenError(Exception): pass
class DeleteTokenError(Exception): pass
class CheckTokenError(Exception): pass
class IsSessionError(Exception): pass
class AccountAddError(Exception): pass
class AccountDelError(Exception): pass
class AccountModError(Exception): pass
class AccountInfoError(Exception): pass
class FingerError(Exception): pass


for key in kbasix:
    vars()[key] = kbasix[key]


def _check_args(args):
    """Check that function arguments are of the proper type.

       (OK, status) = _check_args(function_arguments)

    Check the type validity of the dictionary values depending on their
    respective keys. The input is a dictionary and the output is the tuple
    (bool, str) which states whether the values are OK or not and a brief
    explanation.
    """
    for key, val in args.items():
        if key in ['login_name', 'access', 'token', 'ext'] and \
                not isinstance(val, basestring):
            return (False, 'Key "%s" is not a string' % key)
        elif key in ['uid'] and not isinstance(val, int):
            return (False, 'Key "%s" is not an integer' % key)
        elif key in ['ip_set', 'first_time', 'required', 'holdover', \
                         'wipe'] and not isinstance(val, bool):
            return (False, 'Key "%s" is not a boolean' % key)
        elif key in ['settings'] and not isinstance(val, dict):
            return (False, 'Key "%s" is not a dict' % key)
    return (True, 'All keys are of the proper type')


def _create_token(req, uid, ip_set=True, access='all'):
    """Create a session ID token for uid.

       token = _create_token(req, uid, ip_set=True, access='all')

    If 'ip_set' is True the token will contain the requesting IP.
    If 'access' is 'all' the token is valid for any module, otherwise
    only the specified modules will be available (as long as they require
    a session token to access). Note that because the way a token is
    constructed the modules should have alnum names (underscores are
    also allowed). Returns the token (a string).
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise CreateTokenError(status)
    from mod_python import apache
    if disallow_multiple_sessions or per_request_token:
        _delete_token(uid, token='*')
    if ip_set:
        ip = req.get_remote_host(apache.REMOTE_NOLOOKUP)
    else:
        ip = '0.0.0.256'
    # Because of "access" modules should have alnum names (underscores are
    # also allowed, but certainly not '-').
    rand_id = hashlib.sha256(os.urandom(random_length)).hexdigest()
    token = '%s-%r-%s-%s-%s-tk' % (uid, \
                                       time.time(), \
                                       rand_id, \
                                       ip, \
                                       access)
    try:
        tf = os.path.join(users_root_dir_, str(uid), token)
        f = open(tf, 'w')
        f.close()
        os.chmod(tf, 0600)
    except Exception as reason:
        raise CreateTokenError(reason)
    return token


def _delete_token(uid, token='*'):
    """Delete a token belonging to uid.

       _delete_token(uid, token='*')

    If 'token' is '*' all the tokens belonging to uid are deleted.
    Success returns nothing, an error triggers 'DeleteTokenError'.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise DeleteTokenError(status)
    user_dir = os.path.join(users_root_dir_, str(uid))
    if token == '*':
        try:
            for i in fnmatch.filter(os.listdir(user_dir), '*-tk'):
                os.remove(os.path.join(user_dir, i))
        except Exception as reason:
            raise DeleteTokenError(reason)
        return
    try:
        os.remove(os.path.join(user_dir, token))
    except Exception as reason:
        raise DeleteTokenError(reason)
    return


def _check_token(token, first_time=False):
    """Checks the syntax and validity of a token.

       token_info = _check_token(token, first_time=False)

    If 'first_time' is True the token's timestamp is checked
    against 'account_confirmation_timeout'. A bad token results
    in an empty dictionary returning, otherwise the following dictionary
    is returned:

    {'token': the token itself,
     'uid': the numeric uid (int),
     'start': the time when the token was created (float),
     'session': the unique session id,
     'client_ip': the client IP (or '0.0.0.256' if not set),
     'access': name of the accessible module or 'all'}
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise CheckTokenError(status)
    if not token:
        return {}
    try:
        [uid, start, session, client_ip, access, ext] = token.split('-')
        start = float(start)
        tf = os.path.join(users_root_dir_, uid, token)
        if not os.path.isfile(tf):
            return {}
        now = time.time()
        if first_time:
            if now - os.stat(tf).st_atime >= account_confirmation_timeout:
                return {}
            else:
                os.utime(tf, (now, now))
        if now - os.stat(tf).st_atime >= session_idle_timeout:
            return {}
        elif not per_request_token and now - start >= session_timeout:
            return {}
        else:
            os.utime(tf, (now, now))
    except Exception as reason:
        raise CheckTokenError(reason)
    return {'token': token, 'uid': int(uid), 'start': start, \
                'session': session, 'client_ip': client_ip, \
                'access': access}


def _is_session(req, required, holdover=False):
    """Checks the validity of a session.

       session = _is_session(req, required, holdover=False)

    If 'first_time' is True the token's timestamp is checked
    against 'account_confirmation_timeout'. The 'required' boolean sets
    whether a login is needed to access the page, and if so performs a
    redirect to the login module 'login.py'. A bad token results
    in an empty dictionary returning, otherwise the following dictionary
    is returned:

    {'token': the token itself,
     'uid': the numeric uid (int),
     'start': the time when the token was created (float),
     'session': the unique session id,
     'client_ip': the client IP (or '0.0.0.256' if not set),
     'access': name of the accessible module or 'all'}
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise IsSessionError(status)
    from mod_python import apache, util
    # Using None actually puts 'None' as the token string on the page,
    # which is undesirable as it checks out True.
    no_session = {'token': '', 'login_name': '', 'uid': '', \
                      'start': '', 'session': '', 'client_ip': '', \
                      'access': ''}
    # We do nothing over unencrypted connections
    if not req.is_https():
        return no_session
    referrer = os.path.basename(req.canonical_filename)
    # A login redirect will not have 'file_tag', so if the user
    # is logged out while in the metadata editor and the logs in
    # the redirect will be to the file manager instead.
    if referrer == 'metaeditor.py':
        referrer = 'file_manager.py'
    if 'token' not in req.form:
        token = ''
    else:
        token = req.form['token']
    session = _check_token(token)
    if session:
        # The following exception may be triggered is a user is deleted
        # mid-session.
        try:
            session['login_name'] = _info(session['uid'])['login_name']
        except:
            session = {}
    # Terminate session if the client IP changes (and ip_set is True)
    if session and per_client_ip_token:
        if session['client_ip'] == '0.0.0.256':
            pass
        elif session['client_ip'] != \
                req.get_remote_host(apache.REMOTE_NOLOOKUP):
            session = {}
    if session and session['access'] not in ['all', referrer]:
        session = {}
    if session and per_request_token:
        # For extra security we create a token per request, except if we
        # explicitly require a holdover (needed when client-based windows
        # are generated e.g. a download query window).
        if holdover:
            return session
        else:
            token = _create_token(req, session['uid'])
            session = _check_token(token)
            if session:
                session['login_name'] = _info(session['uid'])['login_name']
    if not session and required:
        util.redirect(req, '../login.py/process?start&referrer=%s' % \
                          referrer)
    if session:
        return session
    else:
        return no_session


def _account_add(login_name, settings):
    """Add a KBasix user account.

       _account_add(login_name, settings)

    The 'settings' dictionary is stored in the user's profile. Its
    only requirement is to define the keys 'user_name' and 'login_name'
    (such that login_name = user_name.lower(), where login_name is
    the user login name handled by the KBasix user management module.
    Returns nothing.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise AccountAddError(status)
    if 'user_name' not in settings:
        raise AccountAddError('Account settings must contain "user_name"')
    user_name = settings['user_name']
    if login_name != settings['login_name']:
        raise AccountAddError('Inconsistent "login_name" ("%s" and "%s")', \
                                  (login_name, settings['login_name']))
    # This 'user_name' is the only user input saved directly on disk and
    # hence the extra security checks (which should never be triggered).
    # Although the length of the variable is set by 'login_name_max_length',
    # it's very hard to believe a user name will be over 100 characters
    # long, and furthermore such long names can cause issues with the
    # filename length limit on the file system (system-dependent, but
    # usually 255 characters).
    if not user_name.isalnum() or len(user_name) > 100:
        raise AccountAddError('Invalid "user_name": %s' % user_name)
    uid = str(_info(login_name)['uid'])
    # The 'world' subdirectory is created, and is in turned symlinked
    # from the overall 'www_dir_' which contains the world-exposed
    # user files. Note that the directory symlink name under 'www_dir_'
    # is the user's user name. Note that the user directories are
    # identified by uid.
    user_dir = os.path.join(users_root_dir_, uid)
    # This 'world_dir' (note the lack of underscore) is the physical
    # 'world' dir which lives under the user's directory within
    # 'users_root_dir_'. 'world_dir_' is the top-level http-accessible
    # directory (which lives within DocumentRoot) and within it the
    # the symlink 'world_link' is created (which uses user name as
    # as opposed to uid -- it is deleted when an account is deleted).
    world_dir = os.path.join(user_dir, 'world')
    world_link = os.path.join(www_dir_, user_name)
    rel_path = os.path.relpath(world_dir, www_dir_)
    profile = os.path.join(user_dir, uid + '.profile')
    preferences = os.path.join(user_dir, uid + '.prefs')
    try:
        if not os.path.isdir(user_dir):
            os.makedirs(user_dir)
            os.chmod(user_dir, 0700)
        if not os.path.isdir(world_dir):
            os.makedirs(world_dir)
            os.chmod(world_dir, 0700)
        if not os.path.islink(world_link):
            os.symlink(rel_path, world_link)
    except Exception as reason:
        raise AccountAddError(reason)
    try:
        _save_file({}, preferences, unlock=False)
        _save_file(settings, profile, unlock=False)
    except Exception as reason:
        raise AccountAddError(reason)
    return


def _account_mod(login_name, ext, settings):
    """Modify a KBasix user account.

       _account_mod(login_name, ext, settings)

    The 'ext' can be 'profile' or 'prefs' depending if a user's
    profile information or preferences are being changed. The
    'settings' is a dictionary. Nothing is returned.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise AccountModError(status)
    uid = str(_info(login_name)['uid'])
    f = os.path.join(users_root_dir_, uid, uid + '.%s' % ext)
    try:
        extfile = _read_file(f)
    except Exception as reason:
        raise AccountModError(reason)
    for key in settings:
        extfile[key] = settings[key]
    try:
        _save_file(extfile, f)
    except Exception as reason:
        raise AccountModError(reason)
    return


def _account_del(login_name, wipe=False):
    """Delete a KBasix user account.

       _account_del(login_name, wipe=False)

    If 'wipe' is True, the user files are deleted. Otherwise it is
    feasable to re-open the account (perhaps even under a different
    user name, if the former has been taken already).
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise AccountDelError(status)
    import manage_users
    user_name = _account_info(login_name, 'profile')['user_name']
    uid = str(_info(login_name)['uid'])
    user_dir = os.path.join(users_root_dir_, uid)
    if not wipe:
        _account_mod(login_name, 'profile', {'login_name': '', \
                                                 'user_name': ''})
    (OK, status) = manage_users._del(login_name)
    if not OK:
        raise AccountDelError(status)
    # We have to remove the world symlink in case we want to re-use the
    # user name.
    try:
        os.remove(os.path.join(www_dir_, user_name))
    except Exception as reason:
        raise AccountDelError(reason)
    if wipe:
        try:
            import shutil
            shutil.rmtree(user_dir)
        except Exception as reason:
            raise AccountDelError(reason)
    return


def _account_info(login_name, ext):
    """Retrieve information about a user account.

       info = _account_info(login_name, ext)

    The 'ext' can be 'profile' or 'prefs' depending if a user's
    profile information or preferences are being accessed. Return
    is a dictionary (possibly an empty one). This function is suitable
    for function calls from other programs.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise AccountInfoError(status)
    user_info = _info(login_name)
    if not user_info:
        return {}
    uid = str(user_info['uid'])
    f = os.path.join(users_root_dir_, uid, uid + '.%s' % ext)
    try:
        return _read_file(f, lock=False)
    except Exception as reason:
        raise AccountInfoError(reason)


def _finger(login_name):
    """Interactively retrieve information about a user account.

       info = _finger(login_name)

    The return type may vary, should only be used interactively.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise FingerError(status)
    import pprint
    user_info = _info(login_name)
    if not user_info:
        return 'User "%s" not found.' % login_name
    uid = str(user_info['uid'])
    f = os.path.join(users_root_dir_, uid, uid + '.%s' % 'profile')
    try:
        return pprint.pprint(_read_file(f, lock=False))
    except Exception as reason:
        raise FingerError(reason)
