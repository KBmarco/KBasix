"""
The configuarion file for the KBasix CMS.
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

"""
Variables available to string substitutions and template pages:

If the variable is a string with no '_' suffix it has access
to all "kbasix" definitions plus the definitions pertaining to
its module dictionary (e.g. "login").

The following are also available (these are session-dependent so,
for example, %(uid)s' is blank if no session is present):

  %(token)s: the session token
  %(uid)s: the numeric uid (int)
  %(start)s: the epoch when the session token was created (float)
  %(session)s: the unique session id
  %(client_ip)s: the client IP (or '0.0.0.256' if not set)
  %(access)s: name of the accessible module or 'all'

In addition, during a session profile variables are available
(additional ones may be present depending on subsequently-added
user profile metadata):

  %(registered)s: when user user originally registered (float)
  %(user_name)s: the member's user name
  %(login_name)s: the user's login name (%(user_name)s.lower())
  %(user_email)s: the user's email address
  %(quota)s: the user's email quota
  %(last_login)s: the user's last login (float)

Variables may, in addition, have further substitutions specified
(these are commented just before the variable entry).

Template pages may have %(details)s if the code provides them. See
the default templates.

If name ends in "_" then no variable substitution is done (unless
specific substitutions are specified in the comment just before the
variable entry).)

Substitutions are done only on strings. No substitutions are done on
booleans, numbers, lists, dictionaries (although dictionary string
entries might allow for substitutions), etc.

Variables defined outside of a dictionary are confined to this file
(for example, 'hour').
"""

# Full path of the KBasix top-level directory (without trailing
# slash):
kbasix_root_ = '/www/kbasix'

# The site's top-level URL:
kbasix_url_ = 'https://rhxpnew.math.utoronto.ca'

# Make sure 'DocumentRoot' in 'httpd.conf' point to:
#   kbasix_root_/web

# Some useful definitions:
hour = 60*60
day = hour*24


## GENERAL
## -------

# The 'kbasix' hash contains setting which pertain to the
# overall workings of the CMS.
kbasix = {}

# Make sure the accounts/groups file exists outside of httpd.conf's
# 'DocumentRoot'. Otherwise make absolutely sure there's an .htaccess
# with a 'deny from all' (or regardless, can't hurt to have it).
kbasix['accounts_file_'] = kbasix_root_ + '/sys/accounts.json'
kbasix['groups_file_'] = kbasix_root_ + '/sys/groups.json'

# 'users_root_dir_' and 'shared_dir_' should also be outside
# 'DocumentRoot'. Furthermore, 'shared_dir_' must contain
# at least one non-numeric character so as to guarantee no UID
# clashes.
kbasix['users_root_dir_'] = kbasix_root_ + '/files'
kbasix['shared_dir_'] = kbasix_root_ + '/files/shared'

# This directory must exist and be located somewhere under 'DocumentRoot'.
kbasix['www_dir_'] = kbasix_root_ + '/web/users'

# World-accessible user directories will be symlinked here
# using the user names e.g.
#   https://www.mykbsite.org/users/Jane 
kbasix['www_url_'] = kbasix_url_ + '/users/'

# This hash will configure multiple LDAP servers.
#
# Allowed for '%(option_)s': any server keys (%(server_)s, %(uri_)s...)
# Allowed for '%(uri_)s': any server keys (%(server_)s, %(uri_)s...)
# Allowed for %(selected_)s: empty string or 'selected'
# Allowed for '%(binddn_)s': '%(user_ldap_name)s'
#
# If '*' is in the 'allowed_reg_users' list then anyone on that LDAP server
# can register (the names in this list correspond to the LDAP names, not
# the login names).  Note that once registered it does not block them from
# login in, it just won't allow for users to register to that LDAP server
# or change their current credentials to use that server/name pair.

option = '<option %(selected_)s value="%(server_)s">%(server_)s</option>\n'
kbasix['ldap_servers'] = { \
       'fake-example': { \
        'server_': 'ldap.example.com', \
        'uri_': 'ldap://%(server_)s', \
        'selected_': '', \
        'binddn_': 'uid=%(user_ldap_name)s,ou=Users,dc=example,dc=com', \
        'option_': option, \
        'allowed_reg_users': ['*'], \
        'ldap_name_max_length': 32, \
        'ldap_name_allowed_chars_': 'a-zA-Z0-9._-', \
        'timeout': 10}, \
       }
# If '*' is in the 'allowed_internal_logins' list then anyone can
# register/login internally. These are user login names, meaning lowercased
# user names e.g. the user name 'JaneDoe89' has the corresponding login
# name 'janedoe89'. If names are removed then those users will not be able
# to log in.
kbasix['allowed_internal_logins'] = ['*']

# For internal use: size of the hashed string.
kbasix['random_length'] = 1000

# Timeout to confirm a new registration. Note that the account is not
# deleted, it just sets the initial token's expiration.
kbasix['account_confirmation_timeout'] = day

# If 'per_request_token' is 'False' a 'session_timeout' can be set so
# as to force sessions to expire (the user must log in again).
# If 'per_request_token' is 'True' then only 'session_idle_timeout'
# is enforced (this is an idleness timeout).
kbasix['session_timeout'] = day
kbasix['session_idle_timeout'] = 60*20

# Controls whether a session can carry over multiple IP addresses. If
# 'True' tokens are tied to a single IP address (i.e. cannot carry over).
kbasix['per_client_ip_token'] = True

# For extra security 'per_request_token' can be set to 'True'. There is a
# price to pay: browser buttons cannot be used, and browsing back to forms
# will blank them out. Can be combined with no client-side caches for extra
# security (see .htaccess file), but using browser navigation will cause
# "expired page" errors (on the plus side nothing is stored on the client).
kbasix['per_request_token'] = False

# Note that if 'per_request_token' is 'True' a user cannot carry on
# multiple sessions simultaneously, in which case the following directive is
# irrelevant.
kbasix['disallow_multiple_sessions'] = True

# Placeholder for missing keys in HTML templates.
# Allowed: %(key)s
kbasix['na_'] = \
    '<font style="color:red;">&lt;Key %(key)s not found&gt;</font>'

# Allowed: %(user_name), %(login_name)s, %(token)s
kbasix['user_name_blurb_'] = "You are: %(user_name)s"

# Allowed: %(header_links)s, %(user_name_blurb)s
kbasix['main_header_'] = """
  <header>
  </header>

  <nav>
    <img class="logo" src="/cms/KBasix.svg" alt="" height=50 width=50 />
    <ul>
      %(header_links)s
    </ul>
    <p class="nav_right">%(user_name_blurb)s</p>
  </nav>
"""

# Modules (*.py) must have alnum names ending in '.py' (underscores are
# also allowed, but '-' are not).

# These are the navigation links in the header. The structure is
# ['name', 'module.py'], and the order corresponds to what is shown.
# Note that if a module requires authentication the login page will
# be automatically displayed.
kbasix['visitor_links'] = [['Main', 'main.py'], \
                               ['Register', 'register.py'], \
                               ['Login', 'login.py']]

# Same as above, but for users who have logged in.
kbasix['user_links'] = [['Main', 'main.py'], \
                            ['Files', 'file_manager.py'], \
                            ['Upload', 'upload.py'], \
                            ['Profile', 'profile.py'], \
                            ['Logout', 'logout.py']]

# The displayed footer times seem to be random... why? Note that
# the token times are fine, and internally things appear to
# be OK, but when displaying these times they often shift
# unpredictably by a few minutes (and not by, say, full
# hours, but 30s, 4m, 76m)... it always seems to lag behind, though.
# Confusingly, this does not happen every time, it starts
# and stops happening randomly. Very confusing...
# EUREKA!
# This file isn't read every time a page is retrieved (if
# the time starts falling behind just touch this file and
# it'll get reloaded). So, be careful about generating
# on-the-fly content in this file. Leaving this comment and code
# for future reference.
# import logging
# logging.basicConfig(level=getattr(logging, \
#                                       'DEBUG'), \
#                         filename=kbasix_root_ + '/logs/kbasix.log', \
#                         datefmt='%a, %d %b %Y %H:%M:%S', \
#                         format='%(levelname)-8s : %(asctime)s : %(filename)s : %(funcName)s : %(lineno)s : %(message)s')
# import time
# now = time.time()
# served = time.strftime('%H:%M:%S on %b %d, %Y', time.localtime(now))
# # This debug only comes up if defs.py changes!
# logging.debug('Epoch: %s' % now)
# # The standard footer.
# kbasix['main_footer_'] = """
# <footer>
#   Served at %s (%s)<br>
#   Powered by KBasix <img class="logo" src="/cms/KBasix.svg"
#   alt="" height=20 width=20 />
# </footer>
# """ % (served, now)

# The standard footer.
kbasix['main_footer_'] = """
<footer>
  Powered by KBasix <img class="logo" src="/cms/KBasix.svg"
  alt="" height=20 width=20 />
</footer>
"""

# The MathJax header string.
kbasix['mathjax_script'] = \
    '<script type="text/javascript" src="/MathJax/MathJax.js?config=default"></script>'

# Generic error blurb.
kbasix['error_blurb_'] = \
    'the administrator has been notified, please try again later'

# Location of the 'status' and 'error' HTML templates.
kbasix['status_page_'] = kbasix_root_ + '/web/cms/status.html'
kbasix['error_page_'] = kbasix_root_ + '/web/cms/error.html'

# The SMTP host.
kbasix['smtp_host_'] = 'localhost'

# Note that %(login_name_max_length)s has an internal 100-character limit
# hard-coded.
kbasix['login_name_max_length'] = 16
kbasix['passwd_length_min'] = 8
kbasix['passwd_letters_min'] = 2
kbasix['passwd_numbers_min'] = 2

# A regexp which checks the validity of an email address.
kbasix['valid_email_'] = '[A-Z0-9._%+-]{1,50}@[A-Z0-9.-]{1,50}\.[A-Z]{2,4}$'
kbasix['email_max_length'] = 100
kbasix['passwd_requirement_'] = """
Minimum password length is %(passwd_length_min)s characters and must
contain at least %(passwd_numbers_min)s numbers and %(passwd_letters_min)s
letters.<br>""" % kbasix

# Location of the log. Should be outside of 'DocumentRoot'
# See: http://docs.python.org/release/2.4.4/lib/minimal-example.html
# for details.
kbasix['log_file_'] = kbasix_root_ + '/logs/kbasix.log'
# Allowed values: debug, info, warning, error, critical
kbasix['log_level_'] = 'debug'
# Allowed: see http://docs.python.org/library/datetime.html
kbasix['log_dateformat_'] = '%a, %d %b %Y %H:%M:%S'
# Allowed: see http://docs.python.org/library/logging.html
kbasix['log_format_'] = \
    '%(levelname)-8s : %(asctime)s : %(filename)s : %(funcName)s : %(lineno)s : %(message)s'

# Blurb on reaching quota limit.
# Extra: %(user_dir_size)s
kbasix['quota_limit_blurb'] = \
    'Quota limit reached (using %(user_dir_size)s out of %(quota)s bytes), you cannot add any more files.'


## MAIN PAGE
## ---------

main = {}
# Location of the main page HTML template.
main['main_page_'] = kbasix_root_ + '/web/cms/main.html'


## LOGIN PAGE
## ----------

login = {}
# Location of the login page HTML template.
login['login_page_'] = kbasix_root_ + '/web/cms/login.html'

# Password reset settings.
login['reset_password_subject'] = 'Password reset solicited'
login['reset_password_blurb'] = \
    'An email has been sent. Please proceed with the password reset.'
# The 'From' address which appears in the password reset email.
login['reset_password_from_email_'] = 'system@reimeika.ca'
# Extras: %(profile_url)s
login['reset_password_notice'] = """
Please go to:

   %(profile_url)s

to reset your password."""

login['welcome_title'] = 'Welcome %(user_name)s!'
login['welcome_blurb'] = 'Please click the button below to continue.'

# List of banned login names.
login['banned_logins'] = ['hana']

# Reasons given to the user for not being able to log in. Using codes
# (e.g. '[01]') minimizes information leakage. Allowed for all (but not
# recommended):
# %(login_name)s, %(user_name)s

# Authentication failure due to non-existence or bad password:
login['reason_auth_fail_'] = 'Access denied [01].'
# Authentication failure due to account lock (i.e. not yet active):
login['reason_not_active_'] = \
    'Access denied (account has yet to be activated).'
# If internal authentication is not allowed:
login['reason_not_allowed_'] = 'Access denied [02].'
# Banned:
login['reason_banned_'] = \
    'The "%(user_name)s" account is currently banned from the system.'


## LOGOUT PAGE
## -----------

logout = {}
logout['goodbye_title'] = 'Goodbye %(user_name)s!'
logout['goodbye_blurb'] = 'You have been logged out.'


## REGISTRATION PAGE
## -----------------

register = {}
register['register_page_'] = kbasix_root_ + '/web/cms/register.html'

# These login names cannot be registered, either because they appear
# to be 'special' e.g. 'admin', or because they are annoying.
register['reserved_login_names'] = ['root', 'super', 'superuser', \
                                        'admin', 'administrator', \
                                        'mod', 'moderator', 'supervisor']
register['blacklisted_login_names'] = ['boob']

# It's recommended that having a letter at the start of the login name
# be enforced.
register['alpha_start_login_name'] = True

# Settings for the email which is sent to complete the registration
# process.
register['email_subject'] = 'Account confirmation required'
register['email_from_'] = 'system@reimeika.ca'
# Extras: %(confirm_url)s
register['confirmation_notice'] = """
Please go to:

   %(confirm_url)s

to confirm your account."""
register['successful_registration_blurb'] = """
The account <strong>%(user_name)s</strong> has been successfully created.
In order to activate it please follow the instructions you will shortly
receive at the <strong>%(user_email)s</strong> email address.<br>"""

# Note that quotas are somewhat soft: they only disallow adding
# files once they have exceeded the alloted space.
register['default_quota'] = 32*1024*1024


## CONFIRMATION PAGE
## -----------------

confirm = {}
confirm['successful_confirmation_blurb'] = \
    'The account <strong>%(user_name)s</strong> has been confirmed and successfully activated.<br>'
confirm['confirmation_title'] = 'Account confirmation'


## PROFILE PAGE
## ------------

profile = {}
profile['profile_page_'] = kbasix_root_ + '/web/cms/profile.html'
# In addition, the 'profile_page' template can handle user metadata
# e.g. %(user_mail)s
profile['successful_update_blurb'] = \
    'The profile for <strong>%(user_name)s</strong> has been successfully updated.<br>'


## UPLOAD PAGE
## ------------

upload = {}
upload['upload_page_'] = kbasix_root_ + '/web/cms/upload.html'
# These are just for conveineince, they are not used for anything
# internally.
upload['file_types'] = ['audio', 'video', 'image', 'document', 'archive', \
                            'other']
# Single-file upload size limit. The following has to be actually enforced
# in the .htaccess file, this is just informative (see upload.py for
# details).
upload['size_limit_'] = '8MB'
# Allowed: %(name)s, %(type)s, %(size)s, %(md5)s
upload['successful_upload_'] = \
    'File "%(name)s" uploaded successfully<br>(type: %(type)s | size: %(size)s | md5sum: %(md5)s)'


## FILE MANAGER PAGE
## -----------------

file_manager = {}
file_manager['file_manager_page_'] = kbasix_root_ + \
    '/web/cms/file_manager.html'
file_manager['file_manager_time_format_'] = '%I:%M%p, %d-%b-%Y'
# File names are preserved when downloaded, unless they originally
# had non-alnum names, in which case those characters are replaced with '_'.
# However, other innocuous non-alnum symbols can be preserved if added to
# this list.
file_manager['allowed_filename_download_non_alnum_'] = \
    ['.', '-', '_', '+', '=']
file_manager['no_files_found_'] = '<p>No files found.</p>'
# Text which replaces a blank file title (not file name) or file
# description.
file_manager['empty_placeholder_'] = ''
# Set whether files shared by a deleted (but not wiped) user remain visible
# to sharees.
file_manager['exusers_cannot_share'] = True
file_manager['allowed_sort_criteria'] = ['timestamp', 'file_title', \
                                             'file_description', \
                                             'file_type', \
                                             'file_name', 'file_size', \
                                             'file_date']
file_manager['default_sort_criteria_'] = \
    file_manager['allowed_sort_criteria'][0]
# Formatting of the icons in the file manager.
# Allowed: file metadata, %(token)s, %(file_date)s, %(shared_status)s,
# %(shared_with_me)s
file_manager['entry_icons_'] = """
        <td class="icon">
          <form action="../file_manager.py/process?action=confirm_delete"
            method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="hidden" name="file_tag" value="%(file_tag)s" />
            <input title="Delete" type="image" alt="Delete"
              src="/cms/delete.png" />
          </form>
        </td>
        <td class="icon">
          <form action="../file_manager.py/process?action=download"
            method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="hidden" name="file_tag" value="%(file_tag)s" />
            <input title="Download" type="image" alt="Download"
              src="/cms/download.png" />
          </form>
        </td>
        <td class="icon">
          <form action="../metaeditor.py/process?start" method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="hidden" name="file_tag" value="%(file_tag)s" />
            <input title="Edit Properties" type="image"
              alt="Edit Properties" src="/cms/edit.png" />
          </form>
        </td>
        <td class="icon">
          <input %(toggle_select)s form="bulk_delete" type="checkbox"
            name="bulk" value="%(file_tag)s" />
        </td>
      </tr>
"""
# Make '0' for unlimited. Does not affect filtering.
file_manager['max_chars_in_title'] = 60
file_manager['max_chars_in_description'] = 100
file_manager['my_file_colour_'] = '#192c4d'
file_manager['other_file_colour_'] = '#555555'
file_manager['copy_file_icon_'] = '/cms/copy_file.png'
file_manager['copy_file_form_style_'] = 'style="display: inline-block"'
file_manager['shared_icon_with_me_'] = '/cms/shared_with_me.png'
file_manager['shared_icon_by_me_selectively_'] = \
    '/cms/shared_by_me_selectively.png'
file_manager['shared_icon_by_me_locally_'] = \
    '/cms/shared_by_me_locally.png'
file_manager['shared_icon_by_me_to_groups_'] = \
    '/cms/shared_by_me_to_groups.png'
file_manager['shared_icon_by_me_to_world_'] = \
    '/cms/shared_by_me_to_world.png'
# Format for each entry in the file manager (normal and condensed views).
# Allowed: file metadata, %(file_size_str)s, %(token)s, %(file_date)s,
# %(shared_status)s, %(title_blurb)s, %(description_blurb)s
file_manager['entry_template_'] = """
      <tr>
        <td class="text">
          <p class="file_title" style="color: %(file_colour)s;">%(shared_status)s %(title_blurb)s</p>
          <p class="file_name">%(copy_file)s File (%(file_type)s): %(file_name)s</p>
          <p class="file_date">Uploaded: %(file_size_str)s on %(file_date)s</p>
          <p class="description">%(description_blurb)s</p>
        </td>
""" + file_manager['entry_icons_']
# Allowed: same as 'entry_template_'
file_manager['condensed_entry_template_'] = """
      <tr>
        <td class="text">
          <p class="condensed_entry">%(copy_file)s %(shared_status)s <font style="color: %(file_colour)s; font-weight: bold;">%(file_name)s</font> (%(file_size_str)s)</p>
        </td>
""" + file_manager['entry_icons_']


## METADATA EDITOR PAGE
## --------------------

metaeditor = {}
metaeditor['metaeditor_page_'] = kbasix_root_ + '/web/cms/metaeditor.html'
metaeditor['successful_update_blurb'] = \
    'The file metadata has been successfully updated.<br>'
# Control how shares that have been shared with deleted users/groups appear.
# Setting 'remove_ex*_shares' to 'False' is not reliable, i.e. the shares
# (labeled '*.#' where '#' is the old uid/gid) may vanish if the metadata
# editor is active during the user/group deletion (the name cached in the
# textarea will be parsed, not found, and removed).
metaeditor['remove_exusers_shares'] = False
metaeditor['remove_exgroups_shares'] = False

# The metaeditor['basic_meta'] dictionary specifies the formatting of the
# user-editable, non-boolean core metadata fields.
#
# The "core metadata" is created upon file upload, and consists of the
# following:
#
#   %(owner)s, %(owner_uid)s, %(uid_shares)s, %(gid_shares)s,
#   %%(local_share)s, (world_share)s, %(timestamp)s, %(file_title)s,
#   %%(file_description)s, (file_type)s, %(file_name)s, %(file_md5sum)s,
#   %%(file_size)s, %(file_tag)s, (magic_type)s, %(custom)s
#
# Some of the "core matadata" may be set to be user-editable. This is done
# by adding it to the metaeditor['basic_meta'] dictionary. Although any and
# all data can be changed, it only makes sense to modify sime fields
# (e.g. %(uid_shares)s, but not %(file_md5sum)s). We call the editable core
# metadata "basic metadata". The metaeditor['basic_meta'] and
# metaeditor['meta_template_'] dictionaries format the user-editable,
# non-boolean basic metadata, the while metaeditor['boolean_meta_'] string
# formats the boolean basic metadata %(local_share)s and %(world_share)s.

metaeditor['basic_meta'] = {'file_title': \
                                {'name': 'File title', \
                                     'help': 'Title of the file'}, \
                                'file_description': \
                                {'name': 'File description', \
                                     'help': 'Description of the contents'}, \
                                'uid_shares': \
                                {'name': 'Share (users)', \
                                     'help': \
                                     'List of users with which to share this file (-user deleted the share and must be deleted to be re-added, *.# no longer exists)'}, \
                                'gid_shares': \
                                {'name': 'Share (groups)', \
                                     'help': \
                                     'List of groups with which to share this file (*.# no longer exists, file is not shared with those members as a group)'}, \
                                'file_type': \
                                {'name': 'File type', \
                                     'help': 'Type of file'}}

# Set the boolean basic metadata.
# Allowed: %(local_share)s, %(world_share)s, %(world_url)s
metaeditor['boolean_meta_'] = """
      <p class="local_share">Share with all registered users
      <input %(local_share)s type="checkbox" name="local_share"
        value="checked" /></p>
      <p class="world_share">World share (anyone can download)
      <input %(world_share)s type="checkbox" name="world_share"
        value="checked" />
      <p class="world_url"><a href="%(world_url)s">%(world_url)s</a></p>
      </p>
"""
# Allowed: file metadata keys and entries
metaeditor['meta_template_'] = """
        <label style="vertical-align: top;">%(name)s</label>
          <textarea class="multiline"
           title="%(help)s"
           name="%(key)s">%(value)s</textarea><br>
"""
