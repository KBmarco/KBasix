"""
The file manager module for the KBasix CMS.
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

class DownloadFileError(Exception): pass
class DeleteFileError(Exception): pass
class CopyFileError(Exception): pass
class CheckFileTagError(Exception): pass


def _initialize(req, info):
    """Initialize the file manager page.

       _initialize(req, info)

    Returns the KBasix file manager page.
    """
    import logging
    import aux
    import cgi
    import manage_kbasix
    logging.debug('Starting the file manager (%s)' % info['login_name'])
    info['user_dir_size'] = aux._bytes_string(aux._get_dir_size(info))
    info['quota'] = aux._bytes_string(info['quota'])
    # Check to see if the files have been bulk-selected.
    if 'toggle_select' in req.form and \
            req.form['toggle_select'].value == 'checked':
        info['toggle_select'] = 'checked'
    else:
        info['toggle_select'] = ''
    # The file manager settings are stored in the user's preferences file.
    prefs = manage_kbasix._account_info(info['login_name'], 'prefs')
    # Default file manager settings.
    if 'file_manager' not in prefs:
        logging.debug('Setting first-time preferences (%s)' % \
                          info['login_name'])
        prefs['file_manager'] = {}
        prefs['file_manager']['hidden_gidloc_shared_files'] = []
        prefs['file_manager']['sort_criteria'] = \
            info['default_sort_criteria_']
        prefs['file_manager']['reverse'] = ''
        prefs['file_manager']['hide_shared'] = ''
        prefs['file_manager']['condensed_view'] = ''
        prefs['file_manager']['keywords'] = ''
    # Update the settings if filtering has been requested.
    for key in prefs['file_manager']:
        if not info['filter']:
            continue
        # This key is not directly changed by editing form values, but by
        # deleting shared entries.
        if key == 'hidden_gidloc_shared_files':
            continue
        if key in req.form:
            # We should use html.escape when migrating to python3
            val = cgi.escape(req.form[key].value, True)
            if key == 'keywords':
                # If the keywords are not decoded here there are problems
                # substituting a mix of unicode and str e.g.:
                #
                #  return '<html><body><p>%s</p><p>%s</p></body></html>' % \
                #   (info['main_header'], prefs['file_manager']['keywords'])
                #
                # fails.
                val = val.decode('utf-8')
            elif val and val \
                    not in info['allowed_sort_criteria'] + ['checked']:
                val = ''
            prefs['file_manager'][key] = val
        # This enables toggling.
        elif key not in req.form and prefs['file_manager'][key]:
            prefs['file_manager'][key] = ''
    # If someone tried to inject an invalid "sort_criteria" it'd be blanked
    # out above, and we fall back on "default_sort_criteria_" (invalid
    # radio buttons are already blanked out).
    if not prefs['file_manager']['sort_criteria']:
        prefs['file_manager']['sort_criteria'] = \
            info['default_sort_criteria_']
    info['sort_criteria_list'] = '\n'
    # Create the sort criteria drop.
    for i in info['allowed_sort_criteria']:
        s = ''
        if i == prefs['file_manager']['sort_criteria']:
            s = 'selected'
        info['sort_criteria_list'] += \
            '<option %s value="%s">%s</option>\n' % \
            (s, i, i.split('_')[-1].capitalize())
    manage_kbasix._account_mod(info['login_name'], 'prefs', prefs)
    info['file_list'] = _get_file_list(info)
    info.update(prefs['file_manager'])
    return aux._fill_page(info['file_manager_page_'], info)


def _check_file_tag(file_tag, login_name):
    """Check the validity of a file tag.

       _check_file_tag(file_tag, login_name)

    Returns nothing if OK, otherwise raises CheckFileTagError.
    """
    import logging
    # A file_tag should always have the following form:
    #
    #   1341888526.096869-e3b5330ed0c12ce1dc243fa53ad9b30c0bcc6f53d285147781cc2acfaee06fee-file
    #
    # Any exception to this means a potential penetration attack,
    # so it's considered a critical error (the integrity of the CMS should
    # remain intact, however).
    try:
        fields = file_tag.split('-')
        if len(fields) != 3:
            raise ValueError
        # By making this a '1' we don't even allow any value starting
        # with a single '.'.
        if float(fields[0]) < 1:
            raise ValueError
        if not fields[1].isalnum():
            raise ValueError
        if fields[2] != 'file':
            raise ValueError
    except:
        logging.critical('Invalid file_tag "%s" (%s)' % \
                             (file_tag, login_name))
        raise CheckFileTagError('Invalid file')
    return


def _get_file_list(info):
    """Get the file listing.

       file_list = _get_file_list(info)

    Returns a string.
    """
    # This function is way too big, it needs to be sensibly split up.
    import logging
    import os
    import fnmatch
    import time
    import aux
    import manage_users
    import manage_kbasix
    login_name = info['login_name']
    logging.debug('Creating a file list (%s)' % login_name)
    prefs = manage_kbasix._account_info(login_name, 'prefs')
    user_dir = os.path.join(info['users_root_dir_'], str(info['uid']))
    entries = {}
    count = {}
    gids = manage_users._info(login_name)['gids']
    # Check for local- and GID-shared files.
    for subdir in ['local'] + [str(i) for i in gids]:
        subpath = os.path.join(info['shared_dir_'], subdir)
        if os.path.exists(subpath):
            # Some house cleaning: delete broken symlinks.
            for i in os.listdir(subpath):
                f = os.path.join(subpath, i)
                # We are lenient with file removals in shared directories
                # because another user might have beat us to it.
                if not os.path.exists(f):
                    try:
                        os.remove(f)
                        logging.info('Deleted broken shared symlink "%s" \
(%s)' % (f, login_name))
                    except Exception as reason:
                        logging.warn(reason)
            for i in fnmatch.filter(os.listdir(subpath), '*-file'):
                rel_path = os.path.relpath(subpath, user_dir)
                src = os.path.join(rel_path, i)
                dst = os.path.join(user_dir, i)
                # Shared entries which are deleted by the user (the
                # sharee) are actually hidden from view by adding them
                # to the 'hidden_gidloc_shared_files' list when the
                # sharee deletes them.
                # Once hidden, local/gid-shared files cannot be recovered
                # unless explicitly re-shared with that user via uid_shares.
                # Note that if the file exists (important if it's a uid
                # point share, which takes precedence) we leave it alone.
                if not os.path.exists(dst) and \
                        i not in \
                        prefs['file_manager']['hidden_gidloc_shared_files']:
                    try:
                        # The target may not exist, but if the link does,
                        # delete it.
                        if os.path.islink(dst + '-id'):
                            os.remove(dst + '-id')
                        os.symlink(src + '-id', dst + '-id')
                    except:
                        logging.error('Cannot link shared id file "%s" \
(%s)' % (src + '-id', login_name))
                    else:
                        if os.path.islink(dst):
                            os.remove(dst)
                        os.symlink(src, dst)
                        logging.debug('Added shared file "%s" -> "%s" \
(%s)' % (src, dst, login_name))
    # Create the listing of the files/symlinks in the user's directory.
    for i in os.listdir(user_dir):
        f = os.path.join(user_dir, i)
        if not os.path.exists(f):
            try:
                os.remove(f)
                logging.info('Deleted broken user symlink "%s" (%s)' % \
                                 (f, login_name))
            except Exception as reason:
                logging.error(reason)
    for i in fnmatch.filter(os.listdir(user_dir), '*-id'):
        f = os.path.join(user_dir, i)
        # This should not normally happen. The magic [:-3] deletes '-id'
        # and leaves the content file name.
        if not os.path.exists(f[:-3]):
            try:
                os.remove(f)
                logging.error('Deleted orphan id file "%s" (%s)' % \
                                  (f, login_name))
            except Exception as reason:
                logging.error(reason)
            continue
        details = manage_users._read_file(f, lock=False)
        # A symlink implies the file is being shared with the user.
        if os.path.islink(f):
            details['shared_with_me'] = True
        else:
            details['shared_with_me'] = False
        for j in ['file_title', 'file_description']:
            if not details[j]: details[j] = info['empty_placeholder_']
        details['file_date'] = \
            time.strftime(info['file_manager_time_format_'], \
                              time.localtime(details['timestamp']))
        # We need the token for the buttons.
        details['token'] = info['token']
        sort_key = details[prefs['file_manager']['sort_criteria']]
        # We pad with zeros to obtain a natural sorting for entries with
        # the same non-string keys e.g. size or timestamp. Padding to 50
        # seems safe, although this is admittedly a magic number
        # (timestamps have less than 20 digits, and files size are smaller
        # than that). Worst case scenario is that the sorting on huge
        # numeric sort keys (larger than 50 digits) will be wrong, but this
        # is unlikely to happen and has no other consequences.
        if not isinstance(sort_key, basestring):
            sort_key = '%r' % sort_key
            sort_key = sort_key.zfill(50)
        # We internally distinguish between identical entry values
        # (say, identical file names), but although lumped together
        # in their proper place within the overall list they are
        # not sub-sorted in any deliberate way.
        if sort_key not in entries:
            count[sort_key] = 1
            entries[sort_key] = details
        else:
            count[sort_key] += 1
            entries[sort_key + ' (%s)' % count[sort_key]] = details
    if prefs['file_manager']['condensed_view']:
        info['template'] = 'condensed_entry_template_'
    else:
        info['template'] = 'entry_template_'
    file_list = ''
    for key in sorted(entries, \
                          reverse=bool(prefs['file_manager']['reverse'])):
        entries[key]['shared_status'] = ''
        entries[key]['file_colour'] = info['my_file_colour_']
        if entries[key]['shared_with_me']:
            # World shares are not symlinked with the individual accounts,
            # and entries which cannot be read any longer are deleted.
            if not entries[key]['local_share'] and \
                    not info['uid'] in entries[key]['uid_shares'] and not \
                    set(gids).intersection(set(entries[key]['gid_shares'])):
                shared_file = \
                    os.path.join(user_dir, entries[key]['file_tag'])
                try:
                    os.remove(shared_file)
                    os.remove(shared_file + '-id')
                except Exception as reason:
                    logging.error(reason)
                continue
            # Don't show the shares made by no-longer-exsting users if
            # 'exusers_cannot_share' is True.
            elif not manage_users._info(entries[key]['owner_uid']) and \
                    info['exusers_cannot_share']:
                continue
            else:
                entries[key]['shared_status'] = """
                 <img src="%s" title="File shared with me by: %s"
                   alt="[File shared with me by: %s]" />
""" % (info['shared_icon_with_me_'], entries[key]['owner'], \
           entries[key]['owner'])
                entries[key]['file_colour'] = info['other_file_colour_']
        if prefs['file_manager']['hide_shared'] and \
                entries[key]['shared_with_me']:
            continue
        # Shared files can be copied internally (it's more efficient than
        # downloading and uploading again).
        entries[key]['copy_file'] = ''
        if entries[key]['shared_with_me']:
            entries[key]['copy_file_icon_'] = info['copy_file_icon_']
            entries[key]['copy_file_form_style_'] = \
                info['copy_file_form_style_'] 
            entries[key]['copy_file'] = """
             <form %(copy_file_form_style_)s
              action="../file_manager.py/process?action=copy_file"
              method="post">
              <input type="hidden" name="token" value="%(token)s" />
              <input type="hidden" name="file_tag" value="%(file_tag)s" />
              <input title="Make a local copy" type="image"
              alt="Make a local copy" src="%(copy_file_icon_)s" />
             </form>
""" % entries[key]
        # Files that are shared (the user being the sharer) are tagged
        # in various ways to indicate this.
        else:
            if entries[key]['world_share']:
                entries[key]['shared_status'] += """
                 <img src="%s" title="File is shared with the world"
                  alt="[File is shared with the world]" />
""" % info['shared_icon_by_me_to_world_']
            if entries[key]['local_share']:
                entries[key]['shared_status'] += """
                 <img src="%s" title="File is shared with registered users"
                  alt="[File is shared with registered users]" />
""" % info['shared_icon_by_me_locally_']
            if entries[key]['gid_shares']:
                entries[key]['shared_status'] += """
                 <img src="%s" title="File is shared with selected groups"
                  alt="[File is shared with selected groups]" />
""" % info['shared_icon_by_me_to_groups_']
            if entries[key]['uid_shares']:
                entries[key]['shared_status'] += """
                 <img src="%s" title="File is shared with selected users"
                  alt="[File is shared with selected users]" />
""" % info['shared_icon_by_me_selectively_']
        # Convert the size to a string with the appropriate unit suffix e.g.
        # 'MB'.
        entries[key]['file_size_str'] = \
            aux._bytes_string(entries[key]['file_size'])
        entries[key]['toggle_select'] = info['toggle_select']
        # Limit the length of titles and descriptions.
        for i in ['description', 'title']:
            if info['max_chars_in_' + i]:
                max_char = len(entries[key]['file_' + i])
                char_num = min(max_char, info['max_chars_in_' + i])
                entries[key][i + '_blurb'] = \
                    entries[key]['file_' + i][:char_num]
                if max_char > char_num:
                    entries[key][i + '_blurb'] += '...'
            else:
                entries[key][i + '_blurb'] = entries[key]['file_' + i]
        # The keyword filter. This is actually a very important
        # functionality, and should be split into its own function.
        # Furthermore, it is currently very weak, and should be drastically
        # improved. Right now is just filters on words in the file title
        # and description, ignoring punctuation. It is also
        # case-insensitive.
        if prefs['file_manager']['keywords']:
            import re
            # Use '[\W_]+' to eliminate underscores. See also:
            #
            # http://stackoverflow.com/questions/6631870/strip-non-alpha-numeric-characters-from-string-in-python-but-keeping-special-cha
            #
            # The 're.U' works on unicode strings.
            nonalnum = re.compile('[\W]+', re.U)
            keywords = set([i.lower() for i in \
                                prefs['file_manager']['keywords'].split()])
            words = [nonalnum.sub('', i.lower()) for i in \
                         entries[key]['file_title'].split()]
            words += [nonalnum.sub('', i.lower()) for i in \
                          entries[key]['file_description'].split()]
            if keywords <= set(words):
                file_list += aux._fill_str(info[info['template']], \
                                               entries[key])
            continue
        file_list += aux._fill_str(info[info['template']], entries[key])
    if not file_list:
        return info['no_files_found_']
    else:
        return file_list


def _get_file_info(file_tag, info):
    """Read the file metadata.

       file_info = _get_file_info(file_tag, info)

    Returns a dictionary with the file metadata (an empty one if
    either the metadata or content file isn't there).
    """
    import logging
    import os
    import manage_users
    logging.debug('Getting file metadata for "%s" (%s)' % \
                      (file_tag, info['login_name']))
    _check_file_tag(file_tag, info['login_name'])
    the_file = os.path.join(info['users_root_dir_'], str(info['uid']), \
                                file_tag)
    the_id_file = the_file + '-id'
    if not os.path.exists(the_id_file) or not os.path.exists(the_file):
        logging.warn('Unable to retrieve file metadata and/or content \
for "%s" (%s)' % (the_id_file, info['login_name']))
        return {}
    return manage_users._read_file(the_id_file, lock=False)


def _confirm_delete(req, info):
    """Query for a file deletion confirmation.

       _confirm_delete(req, info)

    Returns a status page.
    """
    import logging
    import aux
    logging.debug('File deletion requested (%s)' % info['login_name'])
    info['file_tag'] = req.form['file_tag'].value
    _check_file_tag(info['file_tag'], info['login_name'])
    file_info = _get_file_info(info['file_tag'], info)
    # There is a check to see whether the file has the
    # appropriate access permissions, but it seems redundant
    # (the file is either deleted now or when the user refreshes
    # the file list). It doesn't hurt to keep, but this check
    # won't be done on bulk deletions, so deleting a single
    # file explicitly or by means of a "single-file-bulk-selection"
    # is slightly different. There's also a slight performance
    # penalty, so the future of the following three lines is not
    # guaranteed.
    denied_page = _check_permissions(file_info, info)
    if denied_page:
        return denied_page
    info['title'] = 'Confirm file deletion'
    info['class'] = 'information'
    info['details'] = 'Really delete file "%s"?' % file_info['file_name']
    info['status_button_1'] = """
          <form action="../file_manager.py/process?action=delete"
            method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="hidden" name="file_tag" value="%(file_tag)s" />
            <input type="submit" value="Delete" />
          </form><br>
""" % info
    info['status_button_2'] = """
          <form action="../file_manager.py/process?start" method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="submit" value="Cancel" />
          </form>
""" % info
    return aux._fill_page(info['status_page_'], info)


def _confirm_bulk_delete(req, info):
    """Query for a multiple file deletion confirmation.

       _confirm_bulk_delete(req, info)

    Returns a status page.
    """
    import logging
    import aux
    logging.debug('Bulk file deletion requested (%s)' % info['login_name'])
    info['title'] = 'Confirm the deletion of selected files'
    files = info['file_tags'] = ''
    n = 0
    if 'bulk' not in req.form or not req.form['bulk']:
        info['details'] = 'No files selected'
        info['class'] = 'warning'
        info['status_button_1'] = aux._go_back_button(req, info['token'])
        info['status_button_2'] = ''
        return aux._fill_page(info['status_page_'], info)
    for file_tag in req.form['bulk']:
        # When only one file is selected.
        if not isinstance(req.form['bulk'], list):
            file_tag = req.form['bulk'].value
        _check_file_tag(file_tag, info['login_name'])
        file_info = _get_file_info(file_tag, info)
        # We're not checking permissions on each file (see the
        # comment in '_confirm_delete'). It'd be a hassle to
        # mess up a carefully selected list of files to announce
        # some of them cannot be deleted, even if the final outcome is
        # the same i.e. getting rid of the file(s). In the end the file(s)
        # will not show up once the file managers refreshes, either
        # because they have been deleted or access to them denied.
        if file_info:
            info['file_tags'] += ' ' + file_tag
            files += file_info['file_name'] + '<br>'
            n += 1
        if not isinstance(req.form['bulk'], list): break
    if n == 0:
        # This could happen is one file is selected via checkbox having
        # been unshared from underneath the user.
        logging.warn('No deletable files found (%s)' % info['login_name'])
        info['class'] = 'warning'
        info['details'] = 'No files which you can delete were found.'
        info['status_button_1'] = """
          <form action="../file_manager.py/process?start" method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="submit" value="Back" />
          </form>
""" % info
        info['status_button_2'] = ''
        return aux._fill_page(info['status_page_'], info)
    elif n == 1:
        q = 'file'
    else:
        q = '%s files' % n
    info['details'] = 'Really delete the following %s?<br>%s' % (q, files)
    info['status_button_1'] = """
          <form action="../file_manager.py/process?action=delete"
            method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="hidden" name="file_tags" value="%(file_tags)s" />
            <input type="submit" value="Delete" />
          </form><br>
""" % info
    info['status_button_2'] = """
          <form action="../file_manager.py/process?start" method="post">
            <input type="hidden" name="token" value="%(token)s" />
            <input type="submit" value="Cancel" />
          </form>
""" % info
    info['class'] = 'information'
    return aux._fill_page(info['status_page_'], info)


def _delete_file(req, info):
    """Delete/hide a file and its respective metadata.

       _delete_file(req, info)

    Returns to the file manager page.
    """
    import logging
    import os
    import manage_kbasix
    if 'file_tag' in req.form:
        file_tags = [req.form['file_tag'].value]
    elif 'file_tags' in req.form:
        file_tags_str = req.form['file_tags'].value
        file_tags = file_tags_str.split()
    for file_tag in file_tags:
        _check_file_tag(file_tag, info['login_name'])
        the_dir = os.path.join(info['users_root_dir_'], str(info['uid']))
        the_file = os.path.join(the_dir, file_tag)
        the_id_file = the_file + '-id'
        # This shouldn't really happen as a file which is no-longer shared
        # doesn't have its symlink removed until the file manager is
        # refreshed.
        if not os.path.exists(the_file):
            logging.warn('File "%s" has vanished (%s)' % \
                             (the_file, info['login_name']))
            continue
        if not os.path.exists(the_id_file):
            logging.warn('The id file "%s" has vanished (%s)' % \
                             (the_id_file, info['login_name']))
            continue
        verb = 'Deleted'
        try:
            # Metadata files are renamed: they are small and keep
            # a history of what was there. This is only done for
            # files the user actually owns.
            if not os.path.islink(the_file):
                os.rename(the_id_file, the_id_file + '-removed')
            else:
                prefs = manage_kbasix._account_info(info['login_name'], \
                                                        'prefs')
                # One-to-one shares are also symlinks, but when deleted
                # those are not hidden "never to be seen again" (i.e. they
                # can be re-shared), but instead just deleted.
                # We can tell if the share is of type GID/local by
                # inspecting the symlink prefix:
                shared_rpath = os.path.relpath(info['shared_dir_'], the_dir)
                if os.readlink(the_file).startswith(shared_rpath) and \
                        file_tag not in \
                        prefs['file_manager']['hidden_gidloc_shared_files']:
                    verb = 'Hid'
                    prefs['file_manager']['hidden_gidloc_shared_files'].append(file_tag)
                os.remove(the_id_file)
                manage_kbasix._account_mod(info['login_name'], 'prefs', \
                                               prefs)
            os.remove(the_file)
        except Exception as reason:
            raise DeleteFileError('Unable to delete file "%s" because \
"%s" (%s)' % (the_file, reason, info['login_name']))
        logging.debug('%s file "%s" (%s)' % \
                          (verb, the_file, info['login_name']))
    return _initialize(req, info)


def _check_permissions(file_info, info):
    """Check access permission on a file.

       _check_permissions(file_info, info)

    Returns a string: empty if access granted or a "denied access" page
    otherwise.
    """
    import aux
    import manage_users
    gids = manage_users._info(info['login_name'])['gids']
    denied_page = ''
    info['title'] = 'File unavailable'
    info['details'] = 'You no longer have access to this file.'
    info['status_button_1'] = """
        <form action="../file_manager.py/process?start" method="post">
        <input type="hidden" name="token" value="%s" />
        <input type="submit" value="Files" />
        </form>
""" % info['token']
    info['status_button_2'] = ''
    info['class'] = 'warning'
    if not file_info:
        denied_page = aux._fill_page(info['status_page_'], info)
    elif not info['uid'] == file_info['owner_uid'] and \
            not file_info['local_share'] and \
            not info['uid'] in file_info['uid_shares'] and \
            not set(gids).intersection(set(file_info['gid_shares'])):
        denied_page = aux._fill_page(info['status_page_'], info)
    return denied_page


def _copy_file(req, info):
    """Copy a file internally (within KBasix).

       _copy_file(req, info)

    Depending on the situation it may return an over-quota page, an
    access denied page or, if successful, the file manager page.
    """
    import logging
    import os
    import hashlib
    import time
    import shutil
    import json
    import manage_users
    import upload
    (info['user_dir_size'], over_page) = upload._check_quota(req, 'copy', \
                                                                 info)
    if info['user_dir_size'] < 0:
        return over_page
    user_dir = os.path.join(info['users_root_dir_'], str(info['uid']))
    hash_val = hashlib.sha256(os.urandom(info['random_length'])).hexdigest()
    dst_file_tag = '%r-%s-file' % (time.time(), hash_val)
    src_file_tag = req.form['file_tag'].value
    _check_file_tag(src_file_tag, info['login_name'])
    file_info = _get_file_info(src_file_tag, info)
    denied_page = _check_permissions(file_info, info)
    if denied_page:
        return denied_page
    src_file = os.path.join(user_dir, src_file_tag)
    src_id_file = src_file + '-id'
    dst_file = os.path.join(user_dir, dst_file_tag)
    dst_id_file = dst_file + '-id'
    id_info = manage_users._read_file(src_id_file, lock=False)
    # We massage the appropriate metadata, removing all previous private
    # information.
    id_info['owner'] = info['login_name']
    id_info['owner_uid'] = info['uid']
    id_info['uid_shares'] = []
    id_info['gid_shares'] = []
    id_info['local_share'] = False
    id_info['world_share'] = False
    id_info['timestamp'] = time.time()
    id_info['file_tag'] = dst_file_tag
    id_info['custom'] = {}
    try:
        f = open(dst_id_file, 'wb')
        json.dump(id_info, f)
        f.close()
        os.chmod(dst_id_file, 0600)
    except Exception as reason:
        logging.critical('Unable to create id file "%s" because "%s" \
(%s)' % (dst_id_file, reason, info['login_name']))
        raise CopyFileError('Unable to create id file')
    try:
        shutil.copy2(src_file, dst_file)
    except Exception as reason:
        logging.critical('Unable to copy file "%s" because "%s" (%s)' % \
                             (src_file, reason, info['login_name']))
        raise CopyFileError('Unable to copy file')
    logging.debug('Copied file "%s" -> "%s" (%s)' % \
                      (src_file, dst_file, info['login_name']))
    return _initialize(req, info)


def _download_file(req, info):
    """Download a file.

       _download_file(req, info)

    Depending on the situation it may return an over-quota page, an
    access denied page or, if successful, nothing (file manager remains
    on-screen).
    """
    import logging
    import os
    import aux
    file_tag = req.form['file_tag'].value
    _check_file_tag(file_tag, info['login_name'])
    file_info = _get_file_info(file_tag, info)
    denied_page = _check_permissions(file_info, info)
    if denied_page:
        return denied_page
    the_file = os.path.join(info['users_root_dir_'], str(info['uid']), \
                                file_tag)
    logging.debug('Downloading file "%s" (%s)' % \
                      (the_file, info['login_name']))
    if not os.access(the_file, os.R_OK):
        logging.error('Cannot read file "%s" (%s)' % \
                          (the_file, info['login_name']))
        raise DownloadFileError('Cannot open file')
    # We sanitize the download filename here.
    file_out = ''
    for i in file_info['file_name'].encode('utf-8'):
        # Spaces must be filled otherwise the file name will be truncated
        if i == ' ':
            file_out += '_'
        elif i.isalnum() or i in \
                info['allowed_filename_download_non_alnum_']:
            file_out += i
        else:
            file_out += '_'            
    req.headers_out['Content-Disposition'] = \
        'attachment; filename=%s' % file_out
    sent = req.sendfile(the_file)
    logging.debug('Downloaded file "%s" (%s)' % \
                      (the_file, info['login_name']))
    return


def process(req):
    """Process the file manager page.

       process(req)
    """
    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page
    from defs import kbasix, file_manager
    info = {}
    info.update(kbasix)
    info.update(file_manager)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for file_manager.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot manage your file over an insecure \
connection.'
        logging.info('Disallowed insecure access to file_manager.py')
        return _fill_page(info['error_page_'], info)
    try:
        # The holdover is required if "per_request_token" is True, and
        # has no effect otherwise. This is needed due to the
        # client-generated download window (which has no concept of the
        # new request token).
        if 'action' in req.form and req.form['action'] == 'download':
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
    info['filter'] = False
    if 'start' in req.form:
        try:
            return _initialize(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to initialize the file manager \
[%s].' % info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif 'action' not in req.form:
        info['details'] = 'No action specified within the file manager.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'filter':
        try:
            info['filter'] = True
            return _initialize(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] File manager error [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'copy_file':
        try:
            return _copy_file(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] File manager error [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'confirm_delete':
        try:
            return _confirm_delete(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] File manager error [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'delete':
        try:
            return _delete_file(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Error deleting file [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'confirm_bulk_delete':
        try:
            return _confirm_bulk_delete(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Error deleting files [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'download':
        try:
            return _download_file(req, info)
        except Exception as reason:
            # Not critical... user-end problem maybe?
            logging.error(reason)
            info['details'] = '[SYS] Unable to download file [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected file manager action.'
        logging.error(info['details'])
        return _fill_page(info['error_page_'], info)
