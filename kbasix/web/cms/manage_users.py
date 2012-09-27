"""
User management module for the KBasix CMS.
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

# First release
#_VERSION = 0.10
# Enhanced password encryption procedure (MDLCH)
_VERSION = 0.11

import time
import os
import json
import shutil
import crypt
# The line above is just to set some "Global definitions" below.
from defs import kbasix


"""
The LDAP_SERVERS minimal template is as follows:

LDAP_SERVERS = { \
'ldap1': { \
 'server_': 'ldap.math.toronto.edu', \
 'uri_': 'ldaps://%(server_)s', \
 'binddn_': 'uid=%(user_ldap_name)s,ou=People,dc=math,dc=toronto,dc=edu', \
 'timeout': 10}, \
'ldap2': { \
 'server_': 'ldap.example.com', \
 'uri_': 'ldap://%(server_)s', \
 'binddn_': 'uid=%(user_ldap_name)s,ou=Users,dc=example,dc=com', \
 'timeout': 5}
}


Regarding crypt: this is system dependent! If the system's crypt
is weak (e.g. "crypt.crypt('hello','ab')" gives "abl0JrMf6tlhw")
consider using "passlib" instead (if you presume it trustworthy...
it's in EPEL). Use, for example:

 from passlib.hash import sha256_crypt
 password = sha256_crypt.encrypt(password)
 if not sha256_crypt.verify(password, accounts[login_name]['password']):
 accounts[login_name][key] = sha256_crypt.encrypt(settings[key])

"""

# Global definitions
LDAP_SERVERS = kbasix['ldap_servers']
# OPENID_SERVERS = kbasix['openid_servers']
ACCOUNTS_FILE = kbasix['accounts_file_']
GROUPS_FILE = kbasix['groups_file_']
# The times are in seconds
LOCK_SLICE = 0.5
LOCK_TIMEOUT = 5


class PadlockError(Exception): pass
class ReadFileError(Exception): pass
class SaveFileError(Exception): pass


def _check_args(args):
    """Check that function arguments are of the proper type.

       (OK, status) = _check_args(function_arguments)

    Check the type validity of the dictionary values depending on their
    respective keys. The input is a dictionary and the output is the tuple
    (bool, str) which states whether the values are OK or not and a brief
    explanation.
    """
    for key, val in args.items():
        if key in ['login_name', 'first_name', 'last_name', 'password', \
                       'name', 'auth_method', 'user_auth_name', \
                       'auth_server', 'is_type', 'group_name', \
                       'group_info', 'file_name', 'action'] and \
                       not isinstance(val, basestring):
            return (False, 'Key "%s" is not a string' % key)
        elif key in ['members'] and not isinstance(val, list):
            return (False, 'Key "%s" is not a list' % key)
        elif key in ['account_id'] and not (isinstance(val, basestring) or \
                                                isinstance(val, int)):
            return (False, 'Key "%s" is not a string or an integer' % key)
        elif key in ['uid', 'gid'] and not isinstance(val, int):
            return (False, 'Key "%s" is not an integer' % key)
        elif key in ['expires'] and not (isinstance(val, float) or \
                                             isinstance(val, int)):
            return (False, 'Key "%s" is not a number' % key)
        elif key in ['lock', 'unlock', 'locked', 'backup'] and \
                not isinstance(val, bool):
            return (False, 'Key "%s" is not a boolean' % key)
        elif key in ['auth_misc', 'account', 'settings'] and \
                not isinstance(val, dict):
            return (False, 'Key "%s" is not a dict' % key)
    return (True, 'All keys are of the proper type')


def _padlock(file_name, action):
    """Lock/unlock a file.

       _padlock(file_name, action)

    The first argument is the full path of the file, the second
    is either 'lock' or 'unlock'. A lock file named 'file_name.lock'
    is created. Re-locking attempts take place every LOCK_SLICE
    until the lock file is considered stale at LOCK_TIMEOUT.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise PadlockError(status)
    lock_file = file_name + '.lock'
    try:
        if action == 'lock':
            if not os.path.isfile(lock_file):
                f = open(lock_file, 'w')
                f.close()
            else:
                start = time.time()
                while True:
                    # Wait to see if lock opens
                    time.sleep(LOCK_SLICE)
                    if not os.path.isfile(lock_file):
                        break
                    if time.time() - start > LOCK_TIMEOUT:
                        # Remove stale lock file
                        os.remove(lock_file)
                        break
                _padlock(file_name, 'lock')
        else:
            if os.path.isfile(lock_file):
                os.remove(lock_file)
    except Exception as reason:
        raise PadlockError('Unable to %s file because "%s": %s' % \
                               (action, reason, file_name))
    return


def _read_file(file_name, lock=True):
    """Read the contents of a JSON file.

       data = _read_file(file_name, lock=True)

    The first argument is the full path of the file, the second
    is a boolean which locks the file if 'True' (so that it cannot
    be changed if the contents are being processed). Returns the
    file contents, usually a dictionary.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise ReadFileError(status)
    if not os.access(file_name, os.R_OK):
        raise ReadFileError('No access to file: %s' % file_name)
    if lock:
        _padlock(file_name, 'lock')
    try:
        data_file = open(file_name, 'rb')
        data = json.load(data_file)
        data_file.close()
    except Exception as reason:
        raise ReadFileError('Unable to open file because "%s": %s' % \
                                (reason, file_name))
    return data


def _save_file(data, file_name, unlock=True, backup=True):
    """Save data to a JSON file.

       _save_file(data, file_name, unlock=True, backup=True)

    Save a JSON-supported object (data) into file_name (full path).
    Unlocking defaults to 'True' (the usual procedure is to lock
    the file, read its contents, modify them, save and unlock, but
    of course creating a new file requires no unlocking). A backup
    file can be optionally created.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        raise SaveFileError(status)
    if os.path.isfile(file_name) and backup:
        try:
            shutil.copyfile(file_name, file_name + '-')
            os.chmod(file_name + '-', 0600)
        except Exception as reason:
            raise SaveFileError('Unable to backup file because "%s": %s' % \
                                    (reason, file_name))
    try:
        data_file = open(file_name, 'wb')
        json.dump(data, data_file)
        data_file.close()
        os.chmod(file_name, 0600)
    except Exception as reason:
        raise SaveFileError('Unable to save file because "%s": %s' % \
                                (reason, file_name))
    finally:
        if unlock:
            _padlock(file_name, 'unlock')
    return


def _init_accounts():
    """Initialize the users and groups accounts files.

       _init_accounts()
    """
    if os.path.isfile(ACCOUNTS_FILE):
        return (False, 'File already exists: %s' % ACCOUNTS_FILE)
    _save_file({}, ACCOUNTS_FILE, unlock=False)
    _save_file({}, GROUPS_FILE, unlock=False)
    return (True, 'Successfully created: "%s" and "%s"' % \
                (ACCOUNTS_FILE, GROUPS_FILE))


def _user_add(login_name, first_name='', last_name='', password='*', \
                  auth_method='', user_auth_name='', auth_server='', \
                  uid=-1, auth_misc={}, expires=-1, locked=True):
    """Add a new user.

       (OK, status) = _user_add(login_name, first_name='', last_name='',
                        password='*', auth_method='', user_auth_name='',
                        auth_server='', uid=-1, auth_misc={},
                        expires=-1, locked=True)

    Create a new user account with name 'login_name'. The default uid
    sets the value to the next available uid (max(uid) + 1). An empty
    'auth_method' implies using the internal auth system, but other
    mechanisms may be implemented (e.g. 'ldap' is also supported). To
    access these other mechanisms 'user_auth_name', 'auth_server' and
    'auth_misc' are provided (the latter being a 'catch-all' dictionary).
    The values for 'expires' (float) and 'locked' (boolean) are just
    to provide access control tidbits, they are not enforced in any
    way (in particular the '_authenticate' function ignores them). Returns
    a (bool, str) tuple stating success (or not) and a status message.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (OK, status)
    if not os.path.isfile(ACCOUNTS_FILE):
        return (False, 'File not found (try "_init_accounts()"): %s' % \
                    ACCOUNTS_FILE)
    accounts = _read_file(ACCOUNTS_FILE)
    # Not true that '' is taken, but it's disallowed anyway.
    if not login_name or login_name in accounts:
        _padlock(ACCOUNTS_FILE, 'unlock')
        return (False, 'The user name "%s" is already taken' % login_name)
    uids = [accounts[key]['uid'] for key in accounts]
    # Note that each person should have a unique UID. Otherwise a future
    # user (with a previously-deleted login name) may be able to access
    # files that the previous user had been allowed to see. Only re-use
    # a UID if it's the same person being re-instated.
    if not uids:
        next_uid = 0
    else:
        next_uid = max(uids) + 1
    if uid == -1:
        # In python integers automatically become long (unlimited precision)
        # if need be.
        uid = next_uid
    else:
        if uid in uids:
            _padlock(ACCOUNTS_FILE, 'unlock')
            return (False, 'The uid %s is already in use (next free uid \
is %s)' % (uid, next_uid))
    if password != '*':
        try:
            password = crypt.crypt(password, salt=crypt.METHOD_SHA512)
        except AttributeError:
            _padlock(ACCOUNTS_FILE, 'unlock')
            return (False, 'Your system lacks a strong enough \
encryption scheme')
    timestamp = time.time()
    accounts[login_name] = {'first_name': first_name, \
                                'last_name': last_name, \
                                'password': password, \
                                'uid': uid, \
                                'auth_method': auth_method, \
                                'user_auth_name': user_auth_name, \
                                'auth_server': auth_server, \
                                'auth_misc': auth_misc, \
                                'expires': expires, \
                                'locked': locked, \
                                'created': timestamp, \
                                'modified': timestamp}
    _save_file(accounts, ACCOUNTS_FILE)
    return (True, 'Account "%s" added successfully' % login_name)


def _check_ldap_login(account, password):
    """Verify LDAP credentials.

       (OK, status) = _check_ldap_login(account, password)

    Check whether the user can successfully authenticate against an
    LDAP server (the user information, including personal LDAP settings,
    being stored in the 'account' dictionary). Incorrect server settings
    and/or credentials return (False, str) explaining the problem,
    or (True, int) with the uid.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (OK, status)
    import ldap
    uri = binddn = details = ''
    for key in LDAP_SERVERS:
        if account['auth_server'] == LDAP_SERVERS[key]['server_']:
            uri = LDAP_SERVERS[key]['uri_'] % LDAP_SERVERS[key]
            binddn = LDAP_SERVERS[key]['binddn_'] % \
                {'user_ldap_name': account['user_auth_name']}
            ldap_timeout = LDAP_SERVERS[key]['timeout']
    if not uri or not binddn:
        return (False, 'Unable to determine LDAP server information')
    # The LDAP module raises an exception if authentication fails:
    #  http://www.packtpub.com/article/installing-and-configuring-the-python-ldap-library-and-binding-to-an-ldap-directory
    #  http://stackoverflow.com/questions/6679910/python-ldap-simple-bind-s-timeout
    try:
        l = ldap.initialize(uri)
        l.set_option(ldap.OPT_NETWORK_TIMEOUT, ldap_timeout)
        l.simple_bind_s(binddn, password)
    except ldap.INVALID_CREDENTIALS:
        return (False, 'Invalid LDAP credentials')
    except:
        return (False, 'Unable to connect to LDAP server "%s" as: %s' % \
                    (uri, binddn))
    finally:
        l.unbind()
    return (True, account['uid'])


def _check_openid_login(account):
    """Verify OPENid credentials.

    Not yet implemented.

    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (OK, status)
    import openid
    url = 'https://www.google.com/accounts/o8/id/'
    oid = account['user_auth_name']
    info = openid.consumer.consumer.Consumer.complete(oid, url)
    print(info)


def _authenticate(login_name, password):
    """Authenticate a user.

       (OK, status) = _authenticate(login_name, password)

    Check whether the user's login credentials are valid. Authentication
    takes place against the user account's 'auth_method'. Returns
    (False, str) if the credentials are incorrect (the string being
    a tag indicating the 'auth_method' which failed), or (True, int)
    where int is the user's uid. Note that this function ignores both
    the 'locked' and 'expires' settings.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (False, 'args')
    accounts = _read_file(ACCOUNTS_FILE, lock = False)
    if login_name not in accounts:
        return (False, 'usr')
    # An empty auth_method falls back on the internal system.
    if not accounts[login_name]['auth_method']:
        if accounts[login_name]['password'] == '*':
            return (False, 'passwd')
        if accounts[login_name]['password'] == \
                crypt.crypt(password, accounts[login_name]['password']):
            return (True, accounts[login_name]['uid'])
        else:
            return (False, 'passwd')
    elif accounts[login_name]['auth_method'] == 'ldap':
        try:
            return _check_ldap_login(accounts[login_name], password)
        except:
            return (False, 'ldap')
    # The 'openid' mechanism is not yet operational. Note that
    # other mechanisms may be added with further elifs.
    elif accounts[login_name]['auth_method'] == 'openid':
        try:
            return _check_openid_login(accounts[login_name], password)
        except:
            return (False, 'openid')
    else:
        return (False, 'auth')


def _group_add(group_name, members=[], group_info='', gid=-1):
    """Add a new group.

       (OK, status) = _group_add(group_name, members=[], group_info='',
                        gid=-1)

    Create a new group with name 'group_name'. Optionally, 'members'
    is a list of login names. The default gid value (-1) actually sets
    the gid to the next available integer (max(gid) + 1). Returns
    a (bool, str) tuple stating success (or not) and a status message.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (OK, status)
    if not os.path.isfile(GROUPS_FILE):
        return (False, 'File not found (try "_init_accounts()"): %s' % \
                    GROUPS_FILE)
    groups = _read_file(GROUPS_FILE)
    if not group_name or group_name in groups:
        _padlock(GROUPS_FILE, 'unlock')
        return (False, 'The group name "%s" is already taken' % group_name)
    gids = [groups[key]['gid'] for key in groups]
    if not gids:
        next_gid = 0
    else:
        next_gid = max(gids) + 1
    if gid == -1:
        gid = next_gid
    else:
        if gid in gids:
            _padlock(GROUPS_FILE, 'unlock')
            return (False, 'The gid %s is already in use \
(next free gid is %s)' % (gid, next_gid))
    # The members must be a list of login_names
    login_names = []
    notes = ''
    for i in members:
        if not isinstance(i, basestring):
            _padlock(GROUPS_FILE, 'unlock')
            return (False, 'The members list must consist of login names')
        account = _info(i)
        if not account:
            notes += 'Warning: account "%s" does not exist, skipping.\n' % i
            continue
        if i not in login_names:
            login_names.append(i)
        else:
            notes += 'Warning: member "%s" was already added the group, \
skipping.\n' % i
    if not login_names:
        notes += 'Warning: will create empty group.\n'
    timestamp = time.time()
    login_names = sorted(list(set(login_names)))
    groups[group_name] = {'members': login_names, \
                              'group_info' : group_info, \
                              'gid': gid, \
                              'created': timestamp, \
                              'modified': timestamp}
    _save_file(groups, GROUPS_FILE)
    return (True, '%sGroup "%s" added successfully' % (notes, group_name))


def _get_type(is_type):
    """Retrieve the appropriate data associated with either an account
    or a group.

       (json_file, num_id, str_id, status) = _user_add(group_name,
                               members=[], group_info='', gid=-1)

    All the return tuple values are strings (in the case of 'num_id'
    it's either the string 'uid' or 'gid', while 'str_id' can be
    'login_name' or 'group_name'). The 'status' is an explanation
    of why a call failed (in which case all other values are None),
    or the string 'OK'.
    """
    # The reason 'str_id' is explicitly unicode is for aesthetics,
    # since JSON stores all strings in unicode and without the u
    # 'finger' would show e.g. u'gid': 1, 'group_name': 'wheel'.
    # Hopefully this will be a moot point in python 3.
    if is_type == 'account':
        json_file = ACCOUNTS_FILE
        num_id = 'uid'
        str_id = u'login_name'
    elif is_type == 'group':
        json_file = GROUPS_FILE
        num_id = 'gid'
        str_id = u'group_name'
    else:
        status = 'The "%s" type is not defined' % is_type
        return (None, None, None, status)
    if not os.path.isfile(json_file):
        status = 'File not found (try "_init_accounts()"): %s' % json_file
        return (None, None, None, status)
    return (json_file, num_id, str_id, 'OK')


def _del(name, is_type='account'):
    """Delete a user or a group.

       (OK, status) = _del(name, is_type='account')

    'name' is either a login or group name. The 'is_type' parameter can
    be 'account' or 'group'. Return is (bool, str).
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (OK, status)
    (json_file, num_id, str_id, status) = _get_type(is_type)
    if status != 'OK':
        return (False, status)
    if not isinstance(name, basestring):
        return (False, 'You must use a %s' % str_id)
    info = _info(name, is_type)
    if not info:
        return (False, '%s "%s" not found' % (is_type.capitalize(), name))
    data = _read_file(json_file)
    del data[name]
    if is_type == 'account':
        if info['groups']:
            grp_data = _read_file(GROUPS_FILE)
            for group in info['groups']:
                grp_data[group]['members'].remove(name)
            _save_file(grp_data, GROUPS_FILE)
    _save_file(data, json_file)
    return (True, '%s "%s" deleted successfully' % \
                (is_type.capitalize(), name))


def _mod(name, settings, is_type='account'):
    """Modify a user or a group.

       (OK, status) = _mod(name, settings, is_type='account')

    'name' is either a login or group name. The 'is_type' parameter can
    be 'account' or 'group'. User/group properties are modified via the
    'settings' dictionary, the keys of which correspond to those from
    the '_user_add'/'_group_add' functions (unknown keys are ignored).
    Return is (bool, str).
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return (OK, status)
    (OK, status) = _check_args(settings)
    if not OK:
        return (OK, status)
    (json_file, num_id, str_id, status) = _get_type(is_type)
    if status != 'OK':
        return (False, status)
    if not isinstance(name, basestring):
        return (False, 'You must use a %s' % str_id)
    data = _read_file(json_file)
    if name not in data:
        _padlock(json_file, 'unlock')
        return (False, '%s "%s" not found' % (is_type.capitalize(), name))
    changes = False
    notes = ''
    if 'password' in settings:
        key = 'password'
        if key not in data[name]:
            notes += 'Ignoring unknown key: %s\n' % key
        else:
            if settings[key] == '*':
                data[name][key] = settings[key]
            else:
                try:
                    data[name][key] = \
                        crypt.crypt(settings[key], \
                                        salt=crypt.METHOD_SHA512)
                except AttributeError:
                    _padlock(json_file, 'unlock')
                    return (False, 'Your system lacks a strong enough \
encryption scheme')
            changes = True
    for key in settings:
        if key == 'password': continue
        if is_type == 'account' and key in ['gids', 'groups']:
            notes += 'Group membership can only be changed by modifying \
groups\n'
        elif key not in data[name]:
            notes += 'Ignoring unknown key: %s\n' % key
        else:
            if key == 'members':
                member_list = settings[key][:]
                for i in settings[key]:
                    if not isinstance(i, basestring):
                        notes += 'The members list must consist of login \
names, skipping "%s"\n' % i
                        member_list.remove(i)
                        continue
                    account = _info(i, is_type = 'account')
                    if not account:
                        notes += 'Unknown account "%s" in members list, \
skipping.\n' % i
                        member_list.remove(i)
                        continue
                members = sorted(list(set(member_list)))
                if data[name][key] == members:
                    notes += 'Membership did not change\n'
                else:
                    data[name][key] = members
                    changes = True
            else:
                data[name][key] = settings[key]
                changes = True
    if changes:
        data[name]['modified'] = time.time()
        _save_file(data, json_file)
        msg = '%s%s "%s" modified successfully' % \
            (notes, is_type.capitalize(), name)
    else:
        _padlock(json_file, 'unlock')
        msg = '%sNo changes made' % notes
    return (True, msg)


def _info(account_id, is_type='account'):
    """Retrieve information about a user or a group.

       info = _info(account_id, is_type='account')

    The 'account_id' can be a login name or numeric uid if 'is_type' is
    'account'. Otherwise, if 'is_type' is 'group', 'account_id' can be
    a group name or numeric gid. Return is a dictionary (possibly an
    empty one). This function never returns the hashed password, and
    should be the one used for function calls from other programs.
    """
    (OK, status) = _check_args(locals())
    if not OK:
        return {}
    (json_file, num_id, str_id, status) = _get_type(is_type)
    if status != 'OK':
        return {}
    data = _read_file(json_file, lock = False)
    if isinstance(account_id, int):
        try:
            name = [key for key in data if \
                        data[key][num_id] == account_id][0]
        except:
            return {}
    else:
        name = account_id
    if name not in data:
        return {}
    else:
        info = data[name]
        info[str_id] = name
        if 'password' in info:
            del info['password']
        if is_type == 'account':
            info[u'groups'] = []
            info[u'gids'] = []
            grp_data = _read_file(GROUPS_FILE, lock = False)
            for group in grp_data:
                if name in grp_data[group]['members']:
                    info['groups'].append(group)
                    info['gids'].append(grp_data[group]['gid'])
        return info


def _finger(account_id='', is_type='account'):
    """Interactively retrieve information about a user or a group.

       info = _finger(account_id='', is_type='account')

    The 'account_id' can be a login name or numeric uid if 'is_type' is
    'account'. Otherwise, if 'is_type' is 'group', 'account_id' can be
    a group name or numeric gid. The return type may vary, and may
    include the hashed password -- this function is for interactive
    usage and should never be used programatically.
    """
    (json_file, num_id, str_id, status) = _get_type(is_type)
    if status != 'OK':
        return 'Unable to finger: %s' % status
    data = _read_file(json_file, lock = False)
    if not data:
        return 'The %ss file is empty' % is_type
    if account_id != '':
        import pprint
        info = _info(account_id, is_type)
        if not info:
            return '%s not found' % is_type.capitalize()
        elif is_type == 'account':
            info[u'password'] = data[info['login_name']]['password']
        return pprint.pprint(info)
    else:
        return sorted([key for key in data])
