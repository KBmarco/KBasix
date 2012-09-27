"""
The profile module for the KBasix CMS.
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

class UpdateError(Exception): pass


def _initialize(info):
    import logging
    import manage_kbasix
    import manage_users
    import aux
    profile = manage_kbasix._account_info(info['login_name'], 'profile')
    if '*' in info['allowed_internal_logins'] or \
            info['login_name'] in info['allowed_internal_logins']:
        info['internal_disabled'] = ''
    else:
        info['internal_disabled'] = 'disabled'
    user = manage_users._info(info['login_name'])
    info['first_name'] = user['first_name']
    info['last_name'] = user['last_name']
    if user['auth_method'] == 'ldap':
        info['use_ldap'] = 'checked'
    else:
        info['use_ldap'] = ''
    info['ldap_options'] = ''
    for key in info['ldap_servers']:
        if user['auth_server'] == info['ldap_servers'][key]['server_']:
            info['ldap_servers'][key]['selected_'] = 'selected'
        info['ldap_options'] += info['ldap_servers'][key]['option_'] % info['ldap_servers'][key]
    info['user_ldap_name'] = user['user_auth_name']
    info.update(profile)
    logging.debug('Starting profile page (%s)' % info['login_name'])
    return aux._fill_page(info['profile_page_'], info)


def _update(req, info):
    import logging
    import re
    import time
    import manage_users
    import manage_kbasix
    import aux
    if '*' in info['allowed_internal_logins'] or \
            info['login_name'] in info['allowed_internal_logins']:
        allow_internal = True
    else:
        allow_internal = False
    profile = {}
    account = {}
    account['first_name'] = req.form['first_name'].value
    account['last_name'] = req.form['last_name'].value
    profile['user_email'] = req.form['user_email'].value
    err = 0
    info['details'] = ''
    if not re.match(info['valid_email_'], profile['user_email'], re.I):
        err += 1
        info['details'] += 'Please input a valid email address.<br>'
    if 'user_password' in req.form:
        info['user_password'] = req.form['user_password'].value
    else:
        info['user_password'] = ''
    info['user_ldap_password'] = req.form['user_ldap_password'].value
    info['user_ldap_name'] = req.form['user_ldap_name'].value
    was_external = manage_users._info(info['login_name'])['auth_method']
    if 'use_ldap' in req.form and info['user_ldap_password']:
        if not info['user_ldap_name']:
            err += 1
            info['details'] += 'Please fill out all the LDAP credentials.<br>'
        else:
                from register import _check_ldap
                info['ldap_server'] = req.form['ldap_server'].value
                if info['ldap_server']:
                    (err, info['details']) = _check_ldap(info, err)
                else:
                    err += 1
                    info['details'] += 'Please specify the LDAP server.<br>'
                if not err:
                    account['password'] = '*'
                    account['auth_method'] = 'ldap'
                    account['auth_server'] = info['ldap_server']
                    account['user_auth_name'] = info['user_ldap_name']
                    if not was_external:
                        info['details'] += 'Authentication is no longer internal.<br>'
    elif info['user_password'] and allow_internal:
        from register import _check_password
        info['user_password_check'] = req.form['user_password_check'].value
        (err, info['details']) = _check_password(info, err)
        if not err:
            account['auth_method'] = ''
            account['auth_server'] = account['user_auth_name'] = ''
            account['password'] = info['user_password']
            if was_external:
                info['details'] += 'Authentication is now internal.<br>'
    else:
        info['details'] += 'Note: no authentication changes made.<br>'
    if not err:
        try:
            manage_kbasix._account_mod(info['login_name'], 'profile', profile)
            manage_users._mod(info['login_name'], account)
        except Exception as reason:
            raise UpdateError(reason)
    if err:
        info['class'] = 'fail'
        info['status_button_1'] = aux._go_back_button(req, info['token'])
        info['status_button_2'] = ''
        logging.debug('Failed profile update because "%s" (%s)' % \
                          (info['details'].replace('<br>',' '), info['login_name']))
    else:
        info['class'] = 'success'
        info['details'] += aux._fill_str(info['successful_update_blurb'], info)
        if info['access'] == 'profile.py':
            info['status_button_1'] = """
          <form action="../login.py/process?start" method="post">
            <input type="submit" value="Login" />
          </form><br>
""" % info
        else:
            info['status_button_1'] = ''
        info['status_button_2'] = ''
        logging.debug('Successful profile update (%s)' % info['login_name'])
    info['title'] = 'User Profile'
    return aux._fill_page(info['status_page_'], info)


def process(req):
    """Process the profile page.

       process(req)
    """
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, profile
    info = {}
    info.update(kbasix)
    info.update(profile)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for profile.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot edit your profile over an insecure \
connection.'
        return _fill_page(info['error_page_'], info)
    try:
        # We need to holdover (which only takes when "per_request_token" is
        # True) because we want to keep the restricted token generated when
        # a password is forgotten. Note that this check should be added to
        # any module which needs to be restricted.
        if 'token' in req.form and '-all-tk' not in req.form['token']:
            session = _is_session(req, required=True, holdover=True)    
        else:
            session = _is_session(req, required=True)
        info.update(session)
        if session['token']:
            profile = _account_info(info['login_name'], 'profile')
            info.update(profile)
    except Exception as reason:
        logging.warn(reason)
        info['details'] = '[SYS] Unable to verify session [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    info['main_header'] = _make_header(info)
    if 'start' in req.form:
        try:
            return _initialize(info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to initialize profile editor \
[%s].' % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif 'action' not in req.form:
        info['details'] = 'No action specified trying to edit profile.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'update':
        try:
            return _update(req, info)
        except UpdateError as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to update the profile \
[%s].' % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to update the profile [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected action trying to update the profile.'
        logging.error(info['details'])
        return _fill_page(info['error_page_'], info)
