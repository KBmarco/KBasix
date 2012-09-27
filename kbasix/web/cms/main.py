"""
The main (welcome) module for the KBasix CMS.
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

"""
Some general notes:

Underscore importance:

  http://wiki.apache.org/mod_python/SecurityConsiderations

We import the modules locally because functions are private (underscore
prefix). If we import globally then, although a call such as:

   https://test.escalator.utoronto.ca/register.py/random

will be forbidden, the call:

   https://test.escalator.utoronto.ca/register.py/random.

will result in a verbose error (unless PythonDebug is Off in python.conf).
"""

def _initialize(info):
    """Initialize the welcome page.

       _initialize(info)

    Returns the KBasix welcome page.
    """
    import aux
    import logging
    logging.debug('Starting main page (%s)' % info['login_name'])
    return aux._fill_page(info['main_page_'], info)


def process(req):
    """Process the welcome page.

       process(req)
    """
    # We import functions "as needed" at this stage, making
    # sure they are private (underscore prefix). The exception
    # is "defs", which are just a bunch of defintions (although
    # any functions defined within it should be made private).
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, main
    # Here and in all other modules the module-specific definitions
    # take precedence over the 'kbasix' ones.
    info = {}
    info.update(kbasix)
    info.update(main)
    import logging
    logging.basicConfig(level=getattr(logging, \
                                          info['log_level_'].upper()), \
                            filename=info['log_file_'], \
                            datefmt=info['log_dateformat_'], \
                            format=info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for main.py')
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
        # We use 'warn' level because the '_is_session' redirect seems to
        # trigger this (if 'required=True') although it's not a critical
        # error.
        logging.warn(reason)
        info['details'] = '[SYS] Unable to verify session [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    info['main_header'] = _make_header(info)
    try:
        return _initialize(info)
    except Exception as reason:
        logging.critical(reason)
        info['details'] = '[SYS] Unable to initialize the main \
page [%s].' % info['error_blurb_']
        return _fill_page(info['error_page_'], info)
