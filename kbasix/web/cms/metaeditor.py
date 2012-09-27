"""
The metadata editor module for the KBasix CMS.
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

class MetaeditorError(Exception): pass
class UpdateError(Exception): pass


def _initialize(req, info):
    """Initialize the metadata editor page.

       _initialize(req, info)

    Returns the KBasix metadata editor page.
    """
    import logging
    import aux
    import file_manager
    file_info = file_manager._get_file_info(info['file_tag'], info)
    # If 'file_info' is empty then that file has been unshared from
    # underneath the user, i.e. they couldn't have edited either way.
    if not file_info or file_info['owner_uid'] != info['uid']:
        info['title'] = 'Metadata unavailable'
        info['details'] = \
            'You cannot edit the metadata of a file you do not own.'
        info['status_button_1'] = """
        <form action="../file_manager.py/process?start" method="post">
        <input type="hidden" name="token" value="%s" />
        <input type="submit" value="Back" />
        </form>
""" % info['token']
        info['status_button_2'] = ''
        info['class'] = 'warning'
        return aux._fill_page(info['status_page_'], info)
    else:
        logging.debug('Starting the metadata editor (%s)' % \
                          info['login_name'])
    info['file_manager_button'] = """
        <form action="../file_manager.py/process?start" method="post">
        <input type="hidden" name="token" value="%s" />
        <input type="submit" value="Files" />
        </form>
""" % info['token']
    entry = {}
    # We need to translate the numeric UIDs and GIDs in actual
    # names. Also, the local and world booleans are converted
    # into their HTML equivalents.
    (entry['uid_shares'], entry['gid_shares'], entry['local_share'], \
         entry['world_share']) = _get_shares(file_info, info)
    # If a file has been shared with the world, i.e. if it's directly
    # available via http the URL is set here.
    if entry['world_share']:
        import manage_kbasix
        import os
        user_name = manage_kbasix._account_info(info['login_name'], \
                                                    'profile')['user_name']
        entry['world_url'] = \
            os.path.join(info['www_url_'], user_name, info['file_tag'])
    else:
        entry['world_url'] = ''
    info['boolean_data'] = aux._fill_str(info['boolean_meta_'], entry)
    # There are four types of metadata:
    #   core metadata: set upon creation e.g. MD5SUM.
    #   basic metadata: non-boolean, user-editable subset of the core 
    #                   metadata e.g. UID shares.
    #   boolean metadata: two booleans which toggles between sharing
    #                     with registered users/world.
    #   custom metadata: metadata created by the user.
    # Note that basic is just an arbitrary distinction, whilst custom is
    # stored under a different key (file_info['custom']). Basic metadata
    # is defined by metaeditor['basic_meta'] in defs.py.
    #
    # The 'meta_template_' is the template defined in defs.py which
    # controls the information and layout of the entry.
    info['basic_data'] = ''
    for key, value in file_info.items():
        if key not in info['basic_meta']:
            continue
        data = {}
        data['key'] = key
        # The shares are replaced by the names, not the numeric values.
        if key in ['uid_shares', 'gid_shares']:
            data['value'] = entry[key]
        else:
            data['value'] = value
        data.update(info['basic_meta'][key])
        info['basic_data'] += aux._fill_str(info['meta_template_'], data)
    info['custom_data'] = ''
    for key, value in file_info['custom'].items():
        data = {}
        data['key'] = key
        data['name'] = key
        data['value'] = value
        data['help'] = ''
        info['custom_data'] += aux._fill_str(info['meta_template_'], data)
    info['file_name'] = file_info['file_name']
    return aux._fill_page(info['metaeditor_page_'], info)


def _get_shares(file_info, info):
    """Convert UIDs/GIDs/boolean shares as stored in the file metadata
    into actual user names/group names/HTML 'checked' (or not).

       (users, groups, local, world) = _get_shares(file_info, info)

    Returns a (list, list, str, str) tuple.
    """
    import logging
    import os
    import manage_kbasix
    import manage_users
    id_file = file_info['file_tag'] + '-id'
    users = []
    for i in file_info['uid_shares']:
        user_info = manage_users._info(i)
        # If 'remove_exusers_shares' is False we'll try to keep
        # the shares of non-existent users (so that if they return
        # they can recover said shares). However, this doesn't work
        # well in practice and the metadata editor might wipe it out
        # during an update. Furthermore, the user might be confused
        # when seeing '*.7' in the list. Same for 'remove_exgroups_shares'.
        if not user_info:
            if not info['remove_exusers_shares']:
                users.append('*.%s' % i)
        else:
            # Users who have deleted the file being shared with them
            # show up with a '-' prefix in the shared user list.
            user_name = \
                manage_kbasix._account_info(user_info['login_name'], \
                                                'profile')['user_name']
            if not os.path.exists(os.path.join(info['users_root_dir_'], \
                                                   str(user_info['uid']), \
                                                   id_file)):
                users.append('-' + user_name)
            else:
                users.append(user_name)
    if users:
        users = ', '.join(users)
    else:
        users = ''
    groups = []
    for i in file_info['gid_shares']:
        group_info = manage_users._info(i, is_type='group')
        if not group_info:
            if not info['remove_exgroups_shares']:
                groups.append('*.%s' % i)
        else:
            groups.append(group_info['group_name'])
    if groups:
        groups = ', '.join(groups)
    else:
        groups = ''
    # The booleans become 'checked' if True, '' otherwise.
    if file_info['local_share']:
        local = 'checked'
    else:
        local = ''
    if file_info['world_share']:
        world = 'checked'
    else:
        world = ''
    return (users, groups, local, world)


def _save_file_info(file_info, file_tag, info, lock=False, backup=False):
    """Save the metadata.

       _save_file_info(file_info, file_tag, info, lock=False, backup=False)

    Returns nothing.
    """
    import logging
    import os
    import file_manager
    import manage_users
    file_manager._check_file_tag(file_tag, info['login_name'])
    id_file = os.path.join(info['users_root_dir_'], str(info['uid']), \
                               file_tag) + '-id'
    manage_users._save_file(file_info, id_file, lock, backup)
    logging.debug('Saved metadata file "%s" (%s)' % \
                      (id_file, info['login_name']))
    return


def _update(req, info):
    """Update the metadata.

       _update(req, info)

    Returns a status web page.
    """
    import logging
    import aux
    import cgi
    import file_manager
    info['file_tag'] = req.form['file_tag'].value
    logging.debug('Updating metadata of "%s" (%s)' % \
                      (info['file_tag'], info['login_name']))
    info['title'] = 'Metadata Editor'
    # This is a generic status button, we make the variable substitutions
    # below.
    info['status_button_1'] = """
    <form action="../metaeditor.py/process?start&file_tag=%(file_tag)s"
     method="post">
      <input type="hidden" name="token" value="%(token)s" />
      <input type="submit" value="Back" />
    </form>
    """
    info['status_button_2'] = ''
    file_manager._check_file_tag(info['file_tag'], info['login_name'])
    file_info = file_manager._get_file_info(info['file_tag'], info)
    if not file_info or file_info['owner_uid'] != info['uid']:
        raise UpdateError('Invalid file ownership "%s" (%s)' % \
                              (info['file_tag'], info['login_name']))
    info['details'] = ''
    form_dict = req.form
    if 'local_share' not in form_dict:
        form_dict['local_share'] = ''
    if 'world_share' not in form_dict:
        form_dict['world_share'] = ''
    # Single quotes are escaped (string is inside '')
    # Without .value: 'file_type': Field('file_type', 'Unknown')
    # With .value: 'file_type': 'Unknown'
    for key, rawval in form_dict.items():
        val = cgi.escape(rawval.value, True)
        if key in info['basic_meta'] or key in \
                ['local_share', 'world_share']:
            if key in ['uid_shares', 'gid_shares', 'local_share', \
                           'world_share']:
                err = ''
                try:
                    val.encode('ascii')
                except:
                    info['class'] = 'fail'
                    info['details'] += 'Shares must be ASCII-encoded'
                    info['status_button_1'] = info['status_button_1'] % info
                    logging.debug('Non-ASCII shares found (%s)' % \
                                      info['login_name'])
                    return aux._fill_page(info['status_page_'], info)
                logging.debug('Processing share "%s" with input value \
"%s" (%s)' % (key, val, info['login_name']))
                # Point shares are done with specific users and groups.
                # Wide shares are with all registered users or the world.
                if key in ['uid_shares', 'gid_shares']:
                    (file_info[key], err) = \
                        _set_point_shares(file_info[key], val, key, info)
                if key in ['local_share', 'world_share']:
                    file_info[key] = \
                        _set_wide_share(file_info[key], val, key, info)
                info['details'] += err
            else:
                file_info[key] = val
        elif key in file_info['custom']:
            file_info[key] = val
        elif key in ['token', 'file_tag', 'action']:
            pass
        else:
            try:
                key.encode('ascii')
            except:
                key = 'non-ASCII key'
            try:
                val.encode('ascii')
            except:
                val = 'non-ASCII value'
            logging.warn('Ignoring unknown key pair "%s: %s" (%s)' % \
                             (key, val, info['login_name']))
    _save_file_info(file_info, info['file_tag'], info)
    logging.debug('Successful metadata update (%s)' % info['login_name'])
    info['class'] = 'success'
    info['details'] += aux._fill_str(info['successful_update_blurb'], info)
    info['status_button_1'] = info['status_button_1'] % info
    return aux._fill_page(info['status_page_'], info)


def _parse_shares(shares, shares_type, info):
    """Parse the string of user/group name shares into a list. Checks
    are made for deleted shares and missing users (prepended by a '-' and
    '*', respectively).

       (ids, err) = _parse_shares(shares, shares_type, info)

    Returns a tuple (list, str) with the uids/gids and an error string
    (if any).
    """
    import logging
    import manage_users
    ids = []
    err = ''
    # Note that the shares have already been forced to be ASCII-encoded in
    # '_update'.
    if shares_type == 'uid_shares':
        shares_type = 'account'
        shares_id = 'uid'
        # You cannot share with yourself
        names = list(set([i.strip().lower() for i in shares.split(',') if \
                              i.strip().lower() != info['login_name']]))
    else:
        # Groups are case-sensitive (since their names are not enforced by
        # manage_kbasix).
        shares_type = 'group'
        shares_id = 'gid'
        names = list(set([i.strip() for i in shares.split(',')]))
    logging.debug('Parsed shares (%s): %s' % (info['login_name'], names))
    if names == ['']:
        return (ids, err)
    for i in names:
        try:
            # _get_shares will prepend the '-' if the share was deleted,
            # and use *.# for deleted users.
            if i[0] == '-':
                i = i[1:]
            if i[0] != '*':
                ids.append(manage_users._info(i, is_type=shares_type)[shares_id])
            else:
                ids.append(int(i.split('.')[-1]))
        except:
            err += 'Ignoring unknown %s "%s"<br>' %  (shares_type, i)
            logging.warn('Ignoring unknown id "%s" (%s)' % \
                             (i, info['login_name']))
    return (sorted(ids), err)


def _make_point_share_links(shared_path_src, shared_path_dst, file_tag):
    """Make the symlinks to the point shares.

       _make_point_share_links(shared_path_src, shared_path_dst, file_tag)

    Returns nothing.
    """
    import os
    rel_path = os.path.relpath(shared_path_src, shared_path_dst)
    shared_file_src = os.path.join(rel_path, file_tag)
    shared_file_dst = os.path.join(shared_path_dst, file_tag)
    # If the link exists we remove it since point shares take
    # precedence over wide shares.
    if os.path.islink(shared_file_dst):
        os.remove(shared_file_dst)
    os.symlink(shared_file_src, shared_file_dst)
    if os.path.islink(shared_file_dst + '-id'):
        os.remove(shared_file_dst + '-id')
    os.symlink(shared_file_src + '-id', shared_file_dst + '-id')
    return


def _del_point_share_links(shared_path_dst, file_tag):
    """Delete the symlinks of the point shares.

       _del_point_share_links(shared_path_dst, file_tag)

    Returns nothing.
    """
    import os
    shared_file_dst = os.path.join(shared_path_dst, file_tag)
    if os.path.islink(shared_file_dst):
        os.remove(shared_file_dst)
    if os.path.islink(shared_file_dst + '-id'):
        os.remove(shared_file_dst + '-id')
    return


def _set_point_shares(old_ids, new_shares, shares_type, info):
    """Set the point shares (with individual users).

       (new_ids, err) = 
           _set_point_shares(old_ids, new_shares, shares_type, info)

    Returns a (list, str) tuple with a list of uids/gids and an error
    string (if any).
    """
    import logging
    import os
    import manage_users
    # We convert the 'new_shares' string into a list of uids/gids.
    (new_ids, err) = _parse_shares(new_shares, shares_type, info)
    if new_ids == old_ids:
        logging.debug('Shares of type "%s" were unchanged (%s)' % \
                          (shares_type, info['login_name']))
        return (old_ids, err)
    shared_path_src = os.path.join(info['users_root_dir_'], \
                                       str(info['uid']))
    # New user shares have symlinks created in the target users'
    # directories.
    if shares_type == 'uid_shares':
        logging.debug('Updating UID shares (%s)' % info['login_name'])
        for uid in old_ids:
            # Delete the no-longer-shared user symlinks.
            if uid not in new_ids:
                shared_path_dst = os.path.join(info['users_root_dir_'], \
                                                   str(uid))
                _del_point_share_links(shared_path_dst, info['file_tag'])
        for uid in new_ids:
            shared_path_dst = os.path.join(info['users_root_dir_'], \
                                               str(uid))
            # Leave the unchanged user shares alone.
            if uid in old_ids:
                continue
            else:
                _make_point_share_links(shared_path_src, shared_path_dst, \
                                            info['file_tag'])
    # New group shares have symlinks created in the appropriate group
    # directories. These directories are created if they don't exist
    # already. They are identified by GID, so if a group is deleted
    # and then a new group with the same GID is created then the members
    # of the new group will have access to these shares.
    elif shares_type == 'gid_shares':
        logging.debug('Updating GID shares (%s)' % info['login_name'])
        for gid in old_ids:
            # Delete the no-longer-shared group symlinks.
            if gid not in new_ids:
                shared_path_dst = os.path.join(info['shared_dir_'], \
                                                   str(gid))
                _del_point_share_links(shared_path_dst, info['file_tag'])
        for gid in new_ids:
            shared_path_dst = os.path.join(info['shared_dir_'], str(gid))
            # Leave the unchanged group shares alone.
            if gid in old_ids:
                continue
            else:
                if not os.path.isdir(shared_path_dst):
                    logging.debug('Creating group-sharing directory "%s" \
(%s)' % (shared_path_dst, info['login_name']))
                    os.mkdir(shared_path_dst)
                    os.chmod(shared_path_dst, 0700)
                _make_point_share_links(shared_path_src, shared_path_dst, \
                                            info['file_tag'])
    return (new_ids, err)


def _set_wide_share(old_share, new_share, share_type, info):
    """Set a wide (registered users or world) share.

       new_share = _set_wide_share(old_share, new_share, share_type, info)

    Returns a boolean depending of whether the sharing is enabled (True)
    or not.
    """
    import logging
    import os
    if new_share == old_share:
        logging.debug('Share of type "%s" was unchanged (%s)' % \
                          (share_type, info['login_name']))
        return old_share
    shared_path_src = os.path.join(info['users_root_dir_'], \
                                       str(info['uid']))
    # The 'local_share' and 'world_share' symlinks are either created or
    # deleted.
    if share_type == 'local_share':
        shared_path_dst = os.path.join(info['shared_dir_'], 'local')
        if not os.path.isdir(shared_path_dst):
            logging.debug('Creating local-sharing directory "%s" \
(%s)' % (shared_path_dst, info['login_name']))
            os.mkdir(shared_path_dst)
            os.chmod(shared_path_dst, 0700)
    # This 'world' directory lives within the user's KBasix home directory,
    # and is symlinked from the global http-accessible directory under
    # DocumentRoot via a symlink named after the user name.
    elif share_type == 'world_share':
        shared_path_dst = os.path.join(shared_path_src, 'world')
    if not new_share:
        shared_file_dst = os.path.join(shared_path_dst, info['file_tag'])
        if os.path.islink(shared_file_dst):
            os.remove(shared_file_dst)
        # The 'world' share has no associated metadata symlink, but the
        # 'local' share does.
        if share_type == 'local_share' and \
                os.path.islink(shared_file_dst + '-id'):
            os.remove(shared_file_dst + '-id')
        logging.debug('Share of type "%s" was deleted (%s)' % \
                          (share_type, info['login_name']))
    else:
        # We use relative paths for portability.
        rel_path = os.path.relpath(shared_path_src, shared_path_dst)
        shared_file_src = os.path.join(rel_path, info['file_tag'])
        shared_file_dst = os.path.join(shared_path_dst, info['file_tag'])
        if not os.path.islink(shared_file_dst):
            os.symlink(shared_file_src, shared_file_dst)
        # The 'world' share has no associated metadata symlink, but the
        # 'local' share does.
        if share_type == 'local_share' and \
                not os.path.islink(shared_file_dst + '-id'):
            os.symlink(shared_file_src + '-id', shared_file_dst + '-id')
        logging.debug('Share of type "%s" was added (%s)' % \
                          (share_type, info['login_name']))
    return new_share


def process(req):
    """Process the metadata editor page.

       process(req)
    """
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, metaeditor
    info = {}
    info.update(kbasix)
    info.update(metaeditor)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for metaeditor.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot edit metadata over an insecure \
connection.'
        logging.info('Disallowed insecure access to metaeditor.py')
        return _fill_page(info['error_page_'], info)
    try:
        session = _is_session(req, required=True)
        info.update(session)
        if session['token']:
            profile = _account_info(info['login_name'], 'profile')
            info.update(profile)
    except Exception as reason:
        logging.warn(reason)
        info['details'] = '[SYS] Unable to verify session [%s].' \
            % info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    info['main_header'] = _make_header(info)
    if 'start' in req.form:
        try:
            info['file_tag'] = req.form['file_tag'].value
            return _initialize(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to initialize metadata editor \
[%s].' % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif 'action' not in req.form:
        info['details'] = 'No action specified trying to edit metadata.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'update':
        try:
            return _update(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to update the metadata [%s].' \
                % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected action trying to update the metadata.'
        logging.error(info['details'])
        return _fill_page(info['error_page_'], info)
