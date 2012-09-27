"""
Auxiliary functions of the KBasix CMS.
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

import os
from defs import kbasix


for key in kbasix:
    vars()[key] = kbasix[key]


def _fill_str(data, keys):
    """Smart string substitution, indicating missing keys.

       _fill_str(data, keys)

    Returns a string.
    """
    while True:
        try:
            return data % keys
        except KeyError as key:
            data = data.replace('%(' + key.args[0] + ')s', na_ % \
                                    {'key': key})
            _fill_str(data, keys)


def _fill_page(page, keys):
    """Read a page and perform a'_fill_str' on it.

       _fill_page(page, keys)

    Returns a string (page).
    """
    try:
        data = open(page).read()
    except Exception as reason:
        return '[SYS] Unable to open file: ' + os.path.basename(page)
    return _fill_str(data, keys)


def _make_header(info):
    """Make the appropriate page header (either for a visitor or a member).

       _make_header(info)

    Returns a string (navigation header).
    """
    header_links = ''
    if info['token']:
        links = user_links
        token_var = '<input type="hidden" name="token" value="%s" />' % \
            info['token']
        name_blurb = _fill_str(user_name_blurb_, info)
    else:
        links = visitor_links
        token_var = ''
        name_blurb = ''
    for link in links:
        # Only show the links the token provides access for.
        if info['token'] and info['access'] not in ['all', link[1]]:
            continue
        header_links += """
        <li>
        <form class="nav_header_form" action="../%s/process?start"
        method="post">
        %s
        <input class="nav_header_input" type="submit" value="%s" />
        </form>
        </li>""" % (link[1], token_var, link[0])
    return main_header_ % {'header_links': header_links, \
                               'user_name_blurb': name_blurb}


def _go_back_button(req, token):
    """Create a 'go back' button.

       _go_back_button(req, token)

    Returns a string (html 'back button').
    """
    if per_request_token:
        # Unfortunately filled fields are lost this way.
        referrer = os.path.basename(req.canonical_filename)
        go_back_button = """
<p>
<form action="../%s/process?start" method="post">
<input type="hidden" name="token" value="%s">
<input type="submit" value="Back" />
</form>
</p>
""" % (referrer, token)
    else:
        go_back_button = """
<p>
<input type="button" value="Back" onclick="goBack()" />
<noscript>(use browser's "Back" button if JavaScript is disabled)</noscript>
</p>
"""
    return go_back_button


def _get_dir_size(info):
    """Calculate a directory's size.

       _get_dir_size(info)

    Returns an int.
    """
    import fnmatch
    user_dir = os.path.join(info['users_root_dir_'], str(info['uid']))
    total_size = 0
    for i in fnmatch.filter(os.listdir(user_dir), '*-file'):
        ipath = os.path.join(user_dir, i)
        if not os.path.islink(ipath):
            total_size += os.path.getsize(ipath)
    return total_size


def _bytes_string(size):
    """Appropriately format a value of bytes in a human-friendly way.

       _bytes_string(size)

    The 'size' is an int, returns a string.
    """
    if size >= 1024**2:
        size = '%sMB' % round(size/1024.0**2, 2)
    elif size >= 1024:
        size = '%sKB' % round(size/1024.0, 2)
    else:
        size = '%sB' % size
    return size
