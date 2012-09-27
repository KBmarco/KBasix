"""
The logout module for the KBasix CMS.
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

def _logout(token, info):
    """Logout a user.

        _logout(token, info)

    Returns the logout status page.
    """
    import logging
    import manage_kbasix
    import aux
    uid = int(token.split('-')[0])
    manage_kbasix._delete_token(uid, token='*')
    info['token'] = ''
    info['title'] = aux._fill_str(info['goodbye_title'], info)
    info['class'] = 'information'
    info['details'] = aux._fill_str(info['goodbye_blurb'], info)
    info['status_button_1'] = ''
    info['status_button_2'] = ''
    info['main_header'] = aux._make_header(info)
    logging.debug('Successful logout (%s)' % info['login_name'])
    return aux._fill_page(info['status_page_'], info)


def process(req):
    """Process the logout page.

       process(req)
    """
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, logout
    info = {}
    info.update(kbasix)
    info.update(logout)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for logout.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
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
    if not info['token']:
        info['title'] = 'Logout'
        info['class'] = 'information'
        info['details'] = 'You are not logged in.'
        info['status_button_1'] = ''
        info['status_button_2'] = ''
        return _fill_page(info['status_page_'], info)
    else:
        try:
            return _logout(info['token'], info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to terminate session [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
