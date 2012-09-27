"""
The registration confirmation module for the KBasix CMS.
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

def _confirm(req, info):
    import logging
    import manage_kbasix
    import manage_users
    import aux
    logging.debug('Starting confirmation')
    info['title'] = aux._fill_str(info['confirmation_title'], info)
    info['status_button_1'] = ''
    info['status_button_2'] = ''
    if 'token' in req.form:
        token = req.form['token']
    else:
        token = ''
    session = manage_kbasix._check_token(token, first_time = True)
    if not session:
        info['class'] = 'fail'
        info['details'] = 'Failed to confirm account due to an invalid or stale token (probably the account confirmation deadline has passed)'
        logging.warn(info['details'] + ' [%s]' % token)
        return aux._fill_page(info['status_page_'], info)
    else:
        session['login_name'] = manage_users._info(session['uid'])['login_name']
        info.update(session)
    manage_users._mod(info['login_name'], {'locked': False})
    manage_kbasix._delete_token(info['uid'])
    profile = manage_kbasix._account_info(info['login_name'], 'profile')
    info.update(profile)
    info['class'] = 'success'
    info['details'] = aux._fill_str(info['successful_confirmation_blurb'], info)
    logging.info('Successfully confirmed account "%s"' % info['login_name'])
    return aux._fill_page(info['status_page_'], info)


def process(req):
    from aux import _make_header, _fill_page
    from defs import kbasix, confirm
    info = {}
    info.update(kbasix)
    info.update(confirm)
    import logging
    logging.basicConfig(level = getattr(logging, info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for confirm.py')
        info['details'] = '[SYS] Invalid request [%s].' % info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot confirm over an insecure connection.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    info['token'] = ''
    info['main_header'] = _make_header(info)
    if 'start' in req.form:
        try:
            return _confirm(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = 'Unable to process confirmation [%s].' % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected action trying to confirm registration.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
