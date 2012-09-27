"""
The login module for the KBasix CMS.
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

class LoginError(Exception): pass
class SendTokenError(Exception): pass


def _initialize(info):
    """Initialize the login page.

       _initialize(info)

    Returns the KBasix login page.
    """
    import logging
    import aux
    logging.debug('Starting login page (%s)' % info['login_name'])
    return aux._fill_page(info['login_page_'], info)


def _login(req, info):
    """Try to login the user, or send an email token if the password is
    forgotten.

       _login(req, info)

    Returns a status page.
    """
    if 'forgot_password' in req.form:
        try:
            return _send_token(req, info)
        except Exception as reason:
            raise SendTokenError(reason)
    import logging
    from mod_python import apache
    import manage_users
    import manage_kbasix
    import time
    import aux
    from mod_python import util
    logging.debug('Starting login process for "%s"' % info['login_name'])
    if '*' in info['allowed_internal_logins'] or \
            info['login_name'] in info['allowed_internal_logins']:
        allow_internal = True
    else:
        allow_internal = False
    password = req.form['user_password'].value
    # Note that '_authenticate' only returns the uid if 'is_usr' is
    # True, otherwise it'll return a keyword specifying the authentication
    # failure point.
    try:
        (is_usr, status) = manage_users._authenticate(info['login_name'], \
                                                          password)
        logging.info('Authentication for "%s" was "%s" with \
status/uid: %s' % (info['login_name'], is_usr, status))
    except Exception as reason:
        raise LoginError(reason)
    blocked = False
    # We don't just show the reasons for authentication failures, but
    # instead use codes defined in 'defs.py' (the log is explicit in this
    # respect).
    if is_usr:
        uid = status
        locked = manage_users._info(info['login_name'])['locked']
        if locked:
            blocked = True
            msg = info['reason_not_active_']
    else:
        blocked = True
        msg = info['reason_auth_fail_']
    if not blocked:
        auth_method = manage_users._info(info['login_name'])['auth_method']
        # An empty 'auth_method' means the auth is internal.
        if not auth_method and not allow_internal:
            blocked = True
            msg = info['reason_not_allowed_']
        elif info['login_name'] in info['banned_logins']:
            blocked = True
            msg = info['reason_banned_']
    if not blocked:
        try:
            info['token'] = manage_kbasix._create_token(req, uid)
            info['user_name'] = \
                manage_kbasix._account_info(info['login_name'], \
                                                'profile')['user_name']
            info['access'] = 'all'
            info['class'] = 'information'
            info['main_header'] = aux._make_header(info)
            info['title'] = aux._fill_str(info['welcome_title'], info)
            info['details'] = aux._fill_str(info['welcome_blurb'], info)
            info['status_button_1'] = """
<form action="../%(referrer)s/process?start" method="post">
<input type="hidden" name="token" value="%(token)s">
<input type="submit" value="Continue" />
</form>
""" % info
            info['status_button_2'] = ''
            manage_kbasix._account_mod(info['login_name'], \
                                           'profile', {'last_login': \
                                                           time.time()})
            logging.info('Successful login from %s (%s)' % \
                             (req.get_remote_host(apache.REMOTE_NOLOOKUP), \
                                  info['login_name']))
            return aux._fill_page(info['status_page_'], info)
        except Exception as reason:
            raise LoginError(reason)
    else:
        info['class'] = 'fail'
        info['title'] = 'Login'
        info['details'] = aux._fill_str(msg, info)
        info['status_button_1'] = aux._go_back_button(req, token = '')
        info['status_button_2'] = ''
        logging.info('Failed login for "%s" because "%s"' % \
                         (info['login_name'], info['details']))
        return aux._fill_page(info['status_page_'], info)


def _send_token(req, info):
    """Send an email token if the password was forgotten.

       _send_token(req, info)

    Returns a status page.
    """
    import logging
    import os
    import manage_kbasix
    import manage_users
    import smtplib
    import aux
    from email.mime.text import MIMEText
    logging.debug('Starting forgotten password procedure for "%s"' % \
                      info['login_name'])
    if not manage_users._info(info['login_name']) or \
            manage_users._info(info['login_name'])['locked'] or \
            info['login_name'] in info['banned_logins']:
        info['class'] = 'fail'
        info['main_header'] = aux._make_header(info)
        info['title'] = 'Password reset'
        info['details'] = 'Either that user name was not found, you are \
not allowed into the system, or the account has yet to be activated.'
        info['status_button_1'] = ''
        info['status_button_2'] = ''
        logging.debug('Token not sent to "%s" because "%s"' % \
                          (info['login_name'], info['details']))
        return aux._fill_page(info['status_page_'], info)
    uid = manage_users._info(info['login_name'])['uid']
    user_email = manage_kbasix._account_info(info['login_name'], \
                                                 'profile')['user_email']
    # The token will only allow access to the profile module (which allows
    # to change the password). It should work from any IP address.
    token = manage_kbasix._create_token(req, uid, ip_set=False, \
                                            access='profile.py')
    www_path = os.path.dirname((req.subprocess_env['SCRIPT_NAME']))
    info['profile_url'] = \
        req.construct_url(www_path + \
                              '/profile.py/process?start&token=%s' % token)
    msg = MIMEText(aux._fill_str(info['reset_password_notice'], info))
    msg['Subject'] = aux._fill_str(info['reset_password_subject'], info)
    msg['From'] = info['reset_password_from_email_']
    msg['To'] = user_email
    s = smtplib.SMTP(info['smtp_host_'])
    s.sendmail(info['reset_password_from_email_'], [user_email], \
                   msg.as_string())
    s.quit()
    info['class'] = 'success'
    info['main_header'] = aux._make_header(info)
    info['title'] = 'Password reset'
    info['details'] = aux._fill_str(info['reset_password_blurb'], info)
    info['status_button_1'] = ''
    info['status_button_2'] = ''
    logging.info('Token sent due to forgotten password by "%s" to "%s"' % \
                     (info['login_name'], user_email))
    return aux._fill_page(info['status_page_'], info)


def process(req):
    """Process the login page.

       process(req)
    """
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, login
    info = {}
    info.update(kbasix)
    info.update(login)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for login.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot login over an insecure connection.'
        logging.info('Disallowed insecure access to login.py')
        return _fill_page(info['error_page_'], info)
    try:
        session = _is_session(req, required=False)
        info.update(session)
        if session['token']:
            profile = _account_info(info['login_name'], 'profile')
            info.update(profile)
    except Exception as reason:
        logging.warn(reason)
        info['details'] = '[SYS] Unable to verify session [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    # This page should not appear to people who are already logged in.
    if info['token']:
        info['details'] = 'You are already logged in as "%s".' % \
            info['user_name']
        logging.debug(info['details'])
        return _fill_page(info['error_page_'], info)
    info['main_header'] = _make_header(info)
    # When a page requires a user to be logged-in it sends its name as
    # "referrer", which is obtained from "req.canonical_filename", and
    # spoofing it shouldn't gain anything other than attempting to access
    # a different URL (which can be done by editing the URL directly
    # anyways).
    if 'referrer' not in req.form:
        info['referrer'] = 'main.py'
    else:
        info['referrer'] = req.form['referrer'].value
    if 'start' in req.form:
        try:
            return _initialize(info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to open login page [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif 'action' not in req.form:
        info['details'] = 'No action specified trying to login.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'login':
        try:
            if not req.form['user_name']:
                info['details'] = 'You must input your user name.'
                return _fill_page(info['error_page_'], info)
            else:
                info['user_name'] = req.form['user_name'].value
                info['login_name'] = info['user_name'].lower()
            return _login(req, info)
        except SendTokenError as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to email new token [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
        except LoginError as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to login [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to login [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected action trying to login.'
        logging.error(info['details'])
        return _fill_page(info['error_page_'], info)
