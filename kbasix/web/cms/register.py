"""
The registration module for the KBasix CMS.
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

class RegisterError(Exception): pass
class ConfirmationEmailError(Exception): pass


def _initialize(info):
    """Initialize the registration page.

       _initialize(info)

    Returns the KBasix registration page.
    """
    import logging
    import aux
    # Only internal and LDAP authentication are currently supported.
    # Other mechanisms may be added by simply imitating how LDAP is done.
    info['ldap_options'] = ''
    for key in info['ldap_servers']:
        info['ldap_options'] += info['ldap_servers'][key]['option_'] % \
            info['ldap_servers'][key]
    logging.debug('Starting registration page (%s)' % info['login_name'])
    return aux._fill_page(info['register_page_'], info)


def _check_password(info, err):
    """Check the validity of a submitted password (when registering).

       (err, details) = _check_password(info, err)

    Returns the total number of error encountered (added to the input
    'err' value), and also appends the respective details about the error
    (as a string).
    """
    import logging
    import re
    logging.debug('Checking internal password for "%s"' % \
                      info['login_name'])
    details = info['details']
    if not info['user_password'] or not info['user_password_check']:
        err += 1
        details = info['details']+'Please type in your password twice.<br>'
    if info['user_password'] != info['user_password_check']:
        err += 1
        details = info['details'] + 'The passwords do not match.<br>'
    if len(info['user_password']) < info['passwd_length_min'] or \
            len(re.sub('[a-zA-Z]', '', info['user_password'])) < \
            info['passwd_numbers_min'] or \
            len(re.sub('[0-9]', '', info['user_password'])) < \
            info['passwd_letters_min']:
        err += 1
        details = info['details'] + info['passwd_requirement_']
    return (err, details)


def _check_ldap(info, err):
    """Check the validity of the LDAP configuration and credentials.

       (err, details) = _check_password(info, err)

    Returns the total number of error encountered (added to the input
    'err' value), and also appends the respective details about the error
    (as a string).
    """
    import logging
    import re
    import ldap
    logging.debug('Checking LDAP password for "%s" as "%s"' % \
                      (info['login_name'], info['user_ldap_name']))
    details = info['details']
    uri = binddn = ''
    try:
        info['ldap_server'].encode('ascii')
    except:
        err += 1
        details += 'LDAP server name (%s) is not ASCII-encoded.<br>' % \
            info['ldap_server']
        return (err, details)
    for key in info['ldap_servers']:
        # We only attempt a connection if the server provided is on
        # the server-side list of allowed LDAP servers.
        if info['ldap_server'] == info['ldap_servers'][key]['server_']:
            if '*' not in info['ldap_servers'][key]['allowed_reg_users'] \
                    and info['user_ldap_name'] not in \
                    info['ldap_servers'][key]['allowed_reg_users']:
                err += 1
                details += 'Forbidden LDAP user registration.<br>'
                return (err, details)
            if len(info['user_ldap_name']) > \
                    info['ldap_servers'][key]['ldap_name_max_length']:
                err += 1
                details += 'LDAP user name is too long.<br>'
                return (err, details)
            # Verify encoding:
            try:
                info['user_ldap_name'].encode('ascii')
            except:
                err += 1
                details += 'LDAP user name must be ASCII.<br>'
                return (err, details)
            # Don't allow forbidden characters in the LDAP user name
            X_chars = '[^%s]' % \
                info['ldap_servers'][key]['ldap_name_allowed_chars_']
            if re.search(X_chars, info['user_ldap_name']):
                err += 1
                details += 'Forbidden characters in LDAP user name.<br>'
                return (err, details)
            uri = info['ldap_servers'][key]['uri_'] % \
                info['ldap_servers'][key]
            binddn = info['ldap_servers'][key]['binddn_'] % \
                {'user_ldap_name': info['user_ldap_name']}
            ldap_timeout = info['ldap_servers'][key]['timeout']
    # If the server was chosen from the drop-down list the following should
    # never happen. If so, it indicates a possible attack.
    if not uri or not binddn:
        err += 1
        details += 'Bad LDAP server: (%s).<br>' % info['ldap_server']
        return (err, details)
    # The LDAP module raises an exception if authentication fails:
    #    http://www.packtpub.com/article/installing-and-configuring-the-python-ldap-library-and-binding-to-an-ldap-directory
    try:
        l = ldap.initialize(uri)
        l.set_option(ldap.OPT_NETWORK_TIMEOUT, ldap_timeout)
        l.simple_bind_s(binddn, info['user_ldap_password'])
    except ldap.INVALID_CREDENTIALS:
        logging.debug('Invalid LDAP credentials as "%s" (%s)' % \
                          (info['user_ldap_name'], info['login_name']))
        err += 1
        details += 'Invalid LDAP credentials.<br>'
        return (err, details)
    except Exception as reason:
        logging.warn('LDAP failed because "%s" as "%s" (%s)' % \
                         (reason, info['user_ldap_name'], \
                              info['login_name']))
        err += 1
        details += 'Unable to connect to LDAP server "%s".<br>' % \
                          info['ldap_server']
        return (err, details)
    finally:
        l.unbind()
    logging.debug('Successful LDAP authentication as "%s" (%s)' % \
                      (info['user_ldap_name'], info['login_name']))
    return (err, details)


def _confirmation_email(req, info):
    """Send a confirmation email to complete registration.

       _confirmation_email(req, info)

    Returns nothing.
    """
    import logging
    import os
    import manage_kbasix
    import manage_users
    import smtplib
    import aux
    from email.mime.text import MIMEText
    logging.debug('Sending confirmation email for "%s"' % \
                      info['login_name'])
    uid = manage_users._info(info['login_name'])['uid']
    # We set 'ip_set=False' so that users can confirm their account
    # from any IP.
    token = manage_kbasix._create_token(req, uid, ip_set=False)
    www_path = os.path.dirname((req.subprocess_env['SCRIPT_NAME']))
    confirm_urn = '/confirm.py/process?start&token=%s' % token
    info['confirm_url'] = req.construct_url(www_path + confirm_urn)
    msg = MIMEText(aux._fill_str(info['confirmation_notice'], info))
    msg['Subject'] = aux._fill_str(info['email_subject'], info)
    msg['From'] = info['email_from_']
    msg['To'] = info['user_email']
    try:
        s = smtplib.SMTP(info['smtp_host_'])
        s.sendmail(info['email_from_'], [info['user_email']], \
                       msg.as_string())
        s.quit()
    except Exception as reason:
        logging.error('Unable to send confirmation email because \
"%s" (%s)' % (reason, info['login_name']))
        raise ConfirmationEmailError(reason)
    logging.debug('Confirmation email sent sucessfully for "%s" to "%s"' % \
                      (info['login_name'], info['user_email']))
    return


def _register(req, info):
    """Perform the registration process.

       _register(req, info)

    Returns the registration status page.
    """
    import logging
    import re
    import time
    import manage_users
    import manage_kbasix
    import aux
    # User names will be unique, case-insensitive and case-aware.
    info['user_name'] = req.form['user_name'].value
    info['login_name'] = info['user_name'].lower()
    logging.info('Registering new account for "%s"' % info['login_name'])
    if '*' in info['allowed_internal_logins'] or \
            info['login_name'] in info['allowed_internal_logins']:
        allow_internal = True
    else:
        allow_internal = False
    info['user_email'] = req.form['user_email'].value
    err = 0
    info['details'] = ''
    # KBasix is not yet tested on different locales, so we enforce
    # ASCII here.
    try:
        info['login_name'].encode('ascii')
        info['user_email'].encode('ascii')
    except:
        err += 1
        info['details'] += 'Your user name and email address must be \
ASCII.<br>'
    if info['login_name'] in info['reserved_login_names']:
        err += 1
        # This might be a lie, but the user need not know that.
        info['details'] += 'That user name is already taken.<br>'
    if info['login_name'] in info['blacklisted_login_names']:
        err += 1
        info['details'] += 'That user name is not permitted.<br>'
    # Keep in mind that, regardless of %(login_name_max_length)s, problems
    # may arise if the file paths are too long (this is an issue with
    # with the fact that the user name is present as part of the "world" 
    # URN). Note that there is a 100 character hard limit, regardless
    # of 'login_name_max_length'.
    if len(info['login_name']) > info['login_name_max_length']:
        err += 1
        info['details'] += 'That user name is too long.<br>'
    if not info['login_name'].isalnum():
        err += 1
        info['details'] += 'Your user name can only contain letters and/or \
numbers.<br>'
    # To avoid UID look-alike names we can set 'alpha_start_login_name'
    if info['alpha_start_login_name'] and len(info['login_name']) > 0 and \
            not info['login_name'][0].isalpha():
        err += 1
        info['details'] += 'The user name must begin with a letter.<br>'
    if len(info['user_email']) > info['email_max_length']:
        err += 1
        info['details'] += 'That email address is too long.<br>'
    if not re.match(info['valid_email_'], info['user_email'], re.I):
        err += 1
        info['details'] += 'Please input a valid email address.<br>'
    if 'use_ldap' in req.form:
        info['user_password'] = '*'
        info['auth_method'] = 'ldap'
        info['ldap_server'] = req.form['ldap_server'].value
        if info['ldap_server']:
            info['user_ldap_name'] = req.form['user_ldap_name'].value
            info['user_ldap_password'] = \
                req.form['user_ldap_password'].value
            (err, info['details']) = _check_ldap(info, err)
        else:
            err += 1
            info['details'] += 'Please specify the LDAP server.<br>'
    elif allow_internal:
        info['user_password'] = req.form['user_password'].value
        info['user_password_check'] = req.form['user_password_check'].value
        info['auth_method'] = ''
        info['ldap_server'] = info['user_ldap_name'] = ''
        (err, info['details']) = _check_password(info, err)
    else:
        err += 1
        info['details'] += 'Unavailable authentication scheme.<br>'
    if not err:
        deadline = time.time() + info['account_confirmation_timeout']
        try:
            (OK, dt) = manage_users._user_add(login_name = \
                                                  info['login_name'], \
                                                  password = \
                                                  info['user_password'], \
                                                  auth_method = \
                                                  info['auth_method'], \
                                                  user_auth_name = \
                                                  info['user_ldap_name'], \
                                                  auth_server = \
                                                  info['ldap_server'], \
                                                  expires = deadline)
            if OK:
                now = time.time()
                profile = {'registered': now, \
                               'login_name': info['login_name'], \
                               'user_name': info['user_name'], \
                               'user_email': info['user_email'], \
                               'quota': info['default_quota'], \
                               'last_login': now}
                manage_kbasix._account_add(info['login_name'], profile)
        except Exception as reason:
            raise RegisterError(reason)
        if not OK:
            err += 1
            info['details'] += dt
        else:
            try:
                _confirmation_email(req, info)
            except:
                err += 1
                info['details'] += 'Unable to send confirmation email.<br>'
    if err:
        info['class'] = 'fail'
        info['status_button_1'] = aux._go_back_button(req, info['token'])
        info['status_button_2'] = ''
        logging.info('Failed account registration for "%s" because "%s"' % \
                         (info['login_name'], \
                              info['details'].replace('<br>',' ')))
    else:
        info['class'] = 'success'
        info['details'] += \
            aux._fill_str(info['successful_registration_blurb'], info)
        info['status_button_1'] = ''
        info['status_button_2'] = ''
        logging.info('Successful account registration for "%s"' % \
                         info['login_name'])
    info['title'] = 'Registration'
    return aux._fill_page(info['status_page_'], info)


def process(req):
    """Process the registration page.

       process(req)
    """
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, register
    info = {}
    info.update(kbasix)
    info.update(register)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for register.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot register over an insecure connection.'
        logging.info('Disallowed insecure access to register.py')
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
    info['main_header'] = _make_header(info)
    if 'start' in req.form:
        try:
            return _initialize(info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to initialize registration \
[%s].' % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif 'action' not in req.form:
        info['details'] = 'No action specified trying to register.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'register':
        try:
            return _register(req, info)
        except RegisterError as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to register [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to register [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected action trying to register.'
        logging.error(info['details'])
        return _fill_page(info['error_page_'], info)
