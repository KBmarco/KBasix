"""
The upload module for the KBasix CMS.
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

class GetFileError(Exception): pass


def _initialize(req, info):
    """Initialize the upload page.

       _initialize(req, info)

    Returns the KBasix upload page.
    """
    import logging
    import aux
    info['user_dir_size'] = aux._bytes_string(info['user_dir_size'])
    info['quota'] = aux._bytes_string(info['quota'])
    info['file_types_list'] = '\n'
    # This list of file types is arbitrary, and soley for the benefit
    # of the uploader (to aid the user in file organization). KBasix
    # does support some manner of magic type determination, but the
    # one provided by the user is not used at all for internal purposes.
    for i in info['file_types']:
        info['file_types_list'] += \
            '<option value="%s">%s</option>\n' % (i, i.capitalize())
    logging.debug('Starting upload page (%s)' % info['login_name'])
    return aux._fill_page(info['upload_page_'], info)


def _fbuffer(f, chunk_size=2**16):
    """Generate buffer file chunks.

       _fbuffer(f, chunk_size = 2**16)

    Returns data chunk generator. See also:
       http://stackoverflow.com/questions/231767/the-python-yield-keyword-explained
    Read the comments in '_get_file' for an explanation of the magic
    number.
    """
    while True:
        chunk = f.read(chunk_size)
        if not chunk: break
        yield chunk


def _get_file(req, info):    
    """Upload a file (-file) and create its associate metadata (-file-id)
    file.

       _get_file(req, info)

    Returns the KBasix upload status page.
    """
    import os
    import cgi
    import time
    import hashlib
    import json
    import aux
    import logging
    from mod_python import apache
    # Definitions.
    # A time/hash pair is something like this:
    #
    # time 1345131658.602529
    # hash 60f6bee3404d57f04bb47d9369da5b20e4e510eb0ced4011f3de065590407399
    #
    # id and hash are the same string
    # '-file' and '-file-id' are those strings, so that time-hash-file-id
    # is something like:
    #
    #   1345131658.602529-60f6bee3404d...407399-file-id
    #
    # id_tag is time-hash
    # file_tag is time-hash-file
    # (this file_tag is also the name of the actual data file)
    # id_file is time-hash-file-id
    # (this id_file is also the name of the actual metadata file)
    id_tag = '%r-%s' % \
        (time.time(), \
             hashlib.sha256(os.urandom(info['random_length'])).hexdigest())
    file_tag = id_tag + '-file'
    # The user directories are determined by their UID. They are created
    # when the account is created. Remember that UID is always an integer.
    file_out = os.path.join(info['users_root_dir_'], str(info['uid']), \
                                file_tag)
    id_file = file_out + '-id'
    fileitem = req.form['file_name']
    # In order to substitute this value into the message strings it must
    # be decoded.
    file_in = fileitem.filename.decode('utf-8')
    if file_in:
        d = hashlib.md5()
        # Buffer size is set to 2^16, a magic number which seems OK,
        # but should be justified (or changed). Upping to 2**24 didn't
        # seem to make a difference. Note this also has to be changed
        # in the _fbuffer function above.
        # Browsers seem to be able to handle files up to 2GB in size.
        # Uploading a 2082168350b binary file on a 100Mb LAN took about
        # 4 minutes.
        # Progress bars are a no-go (for now?):
        #   http://www.mailinglistarchive.com/mod_python@modpython.org/msg01880.html
        logging.info('Starting to upload "%s" (%s)' % \
                         (file_out, info['login_name']))
        try:
            f = open(file_out, 'wb', 2**16)
            for chunk in _fbuffer(fileitem.file):
                d.update(chunk)
                f.write(chunk)
        except Exception as reason:
            logging.error('Unable to upload the file type because \
"%s" (%s)' % (reason, info['login_name']))
            raise GetFileError('Upload failed, closing "%s"' % file_out)
        finally:
            f.close()
        os.chmod(file_out, 0600)
        s = os.path.getsize(file_out)
        # You can add to the "id_info" dictionary any other metadata
        # you wish to save, but the following is the basic information
        # all files will contain.
        id_info = {}
        id_info['owner'] = info['login_name']
        id_info['owner_uid'] = info['uid']
        id_info['uid_shares'] = []
        id_info['gid_shares'] = []
        id_info['local_share'] = False
        id_info['world_share'] = False
        id_info['timestamp'] = time.time()
        id_info['file_title'] = req.form['file_title'].value
        id_info['file_description'] = req.form['file_description'].value
        file_type = req.form['file_type'].value
        if file_type not in info['file_types']:
            id_info['file_type'] = 'Unknown'
        else:
            id_info['file_type'] = file_type
        id_info['file_name'] = file_in
        id_info['file_md5sum'] = d.hexdigest()
        id_info['file_size'] = s
        id_info['file_tag'] = file_tag
        # Documentation for python-magic seems non-existent, but it seems
        # to be equivalent to the "file" command (which isn't that great).
        try:
            import magic
            magic_type = magic.open(magic.MAGIC_NONE)
            magic_type.load()
            id_info['magic_type'] = magic_type.file(file_out)
        except Exception as reason:
            logging.error('Unable to determine the file type because \
"%s" (%s)' % (reason, info['login_name']))
            id_info['magic_type'] = 'Unknown'
        id_info['custom'] = {}
        for key in id_info:
            if isinstance(id_info[key], basestring):
                # We should use html.escape when migrating to python3
                id_info[key] = cgi.escape(id_info[key], True)
        try:
            f = open(id_file, 'wb')
            json.dump(id_info, f)
        except Exception as reason:
            logging.error('Unable to create the metadata file because \
"%s" (%s)' % (reason, info['login_name']))
            if os.isfile(file_out):
                os.remove(file_out)
            raise GetFileError('Metadata creation failed, deleted upload \
file "%s" and closing "%s"' % (file_out, id_file))
        finally:
            f.close()
        os.chmod(id_file, 0600)
        n = id_info['file_name']
        if s == 0:
            info['class'] = 'warning'
            info['details'] = 'File "%s" uploaded but empty (it may be \
client-side unreadable)' % n
        else:
            s = aux._bytes_string(s)
            info['class'] = 'success'
            info['details'] = aux._fill_str(info['successful_upload_'], \
                                                {'name': \
                                                     id_info['file_name'], \
                                                     'type': \
                                                     id_info['file_type'], \
                                                     'size': s, \
                                                     'md5': d.hexdigest()})
        logging.info('Finished uploading and saving "%s" (%s)' % \
                         (file_out, info['login_name']))
    else:
        info['class'] = 'fail'
        info['details'] = 'No file was specified.'
    info['title'] = 'File Upload'
    # We don't use the usual "go back" button because it will show the
    # upload animation.
    info['status_button_1'] = """
    <form action="../upload.py/process?start" method="post">
      <input type="hidden" name="token" value="%(token)s" />
      <input type="submit" value="Back" />
    </form>
    """ % info
    info['status_button_2'] = ''
    return aux._fill_page(info['status_page_'], info)


def _check_quota(req, up_type, info):
    """Check the user's quota. 'up_type' is a string such as 'upload'
    or 'copy', depending on how the file is being added. Only '-file'
    files are counted towards quota.

       (user_dir_size, status) = _check_quota(req, up_type, info)

    Returns an (int, str) tuple with the user's space usage and
    an empty string if underquota, the number -1 and a "you are
    over quota" page (as a string) if overquota. Note that the quota
    doesn't impede a user from going over it, it just disallows
    adding files after it has been exceeded. Worst case scenario
    uses up approximately 'quota + max upload size'.
    """
    import aux
    import logging
    user_dir_size = aux._get_dir_size(info)
    logging.debug('Space usage: %s/%s (%s)' % \
                      (user_dir_size, info['quota'], info['login_name']))
    if user_dir_size >= info['quota']:
        info['user_dir_size'] = user_dir_size
        info['details'] = aux._fill_str(info['quota_limit_blurb'], info)
        info['class'] = 'fail'
        info['status_button_1'] = aux._go_back_button(req, info['token'])
        info['status_button_2'] = ''
        logging.info('File %s forbidden due to quota limits (%s)' % \
                         (up_type, info['login_name']))
        info['title'] = up_type.capitalize()
        return (-1, aux._fill_page(info['status_page_'], info))
    else:
        return (user_dir_size, '')


def process(req):
    """Process the upload page.

       process(req)
    """
    # Note that upload sizes can be configured via "LimitRequestBody"
    # either in .htaccess or httpd.conf (the latter requires an httpd
    # restart). However, doing so results in mod_python spitting out a
    # nasty error message ("Request Entity Too Large") upon hitting said
    # limit. See:
    #
    #   http://www.mail-archive.com/django-users@googlegroups.com/msg87503.html
    #
    # We can somewhat gracefully bypass this behaviour by adding the
    # following to .htaccess (using 10485760 as an example, and keeping in
    # mind that on a production server PythonDebug should be Off in
    # python.conf):
    #
    #  PythonDebug Off
    #  LimitRequestBody 10485760
    #  ErrorDocument 413 /path/upload.py/process?file_limit=10485760
    #  ErrorDocument 500 "An error was encountered"
    #
    # Note that the ErrorDocument message should be small (see below), and
    # that the paths are relative to DocumentRoot.
    #
    # Now, this approach has the following issue: the file is _not_
    # uploaded to the server, but instead seems to be stored on the client
    # side and for some reason takes a long time to process there
    # (strangely so, as it's not being transferred). This method seems to
    # work well for medium-sized files above LimitRequestBody, but then for
    # huge files the client shows a connection reset error, explained here:
    #
    #   http://stackoverflow.com/questions/4467443/limitrequestbody-doesnt-respond-with-413-for-large-file25mb
    #
    # In spite of the fact that the client feedback is slow (and that the
    # connection is reset on large files) it may be worthwhile to keep
    # since at least this does limit the resources used on the server,
    # including avoiding the "phantom file" space usage on /tmp (downloads
    # are stored in /tmp as a "phantom file", its usage can be obtained via
    # "df", freeing it requires an httpd restart if the upload happens to
    # die in one of the "file too large" manners [just closing the tab does
    # not cause this]).
    #
    # In short:
    #
    #   0                < size <  LimitRequestBody: Upload success ful (OK)
    #   LimitRequestBody < size <  ~1GB            : Upload limit message
    #                                                                   (OK)
    #   ~1GB             < size <  ~2GB            : Connection reset (file
    #                                                             too large)
    #   ~2GB             < size                    : Browsers barf (file
    #                                                             too large)

    from manage_kbasix import _is_session, _account_info
    from aux import _make_header, _fill_page, _fill_str, _go_back_button
    from defs import kbasix, upload
    info = {}
    info.update(kbasix)
    info.update(upload)
    import logging
    logging.basicConfig(level = getattr(logging, \
                                            info['log_level_'].upper()), \
                            filename = info['log_file_'], \
                            datefmt = info['log_dateformat_'], \
                            format = info['log_format_'])
    if repr(type(req)) != "<type 'mp_request'>":
        logging.critical('Invalid request for upload.py')
        info['details'] = '[SYS] Invalid request [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)

    # The following 'file_limit' comes from the 413 error redirect in
    # .htaccess. We disallow sneakiness by making sure the only argument
    # is an integer. Furthermore we note that no session handling is done
    # by this point (so, although the error page has no tokens, the browser
    # "Back" button will take us to our upload page, regardless of whether
    # the tokens are per-request). Since it's a dead-end error page with
    # no user-data it shouldn't affect the fact it lives outside a session's
    # scope.

    # Although the uploads page is session-protected the upload-limit error
    # message has to be public as we can't get the token from
    # .htaccess. Furthermore, it seems this message has to be pretty small
    # (returning "status_page_" gives "Request Entity Too Large"). Note
    # that the user temporarily loses their token, but has no other option
    # other than to browse "Back", recovering their token (also important
    # because HTTPS isn't required either).

    if 'file_limit' in req.form:
        file_limit = req.form['file_limit'].value
        try:
            max_size = int(file_limit)
        except:
            info['details'] = 'Non-numerical upload size'
            logging.error(info['details'] + ': %s' % file_limit)
            return _fill_page(info['error_page_'], info)
        info['details'] = 'The file you are trying to upload is too \
large (max size = %s bytes).' % max_size
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    if not req.is_https():
        info['details'] = 'You cannot upload over an insecure connection.'
        logging.info(info['details'])
        return _fill_page(info['error_page_'], info)
    try:
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
    # User cannot upload if over-quota.
    try:
        (info['user_dir_size'], over_page) = \
            _check_quota(req, 'upload', info)
    except Exception as reason:
        logging.critical(reason)
        info['details'] = '[SYS] Unable to determine quota [%s].' % \
            info['error_blurb_']
        return _fill_page(info['error_page_'], info)
    if info['user_dir_size'] < 0:
        return over_page
    if 'start' in req.form:
        try:
            return _initialize(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Unable to initialize upload [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    elif 'action' not in req.form:
        info['details'] = 'No action specified trying to upload.'
        logging.warn(info['details'])
        return _fill_page(info['error_page_'], info)
    elif req.form['action'] == 'upload_file':
        try:
            return _get_file(req, info)
        except Exception as reason:
            logging.critical(reason)
            info['details'] = '[SYS] Error uploading file [%s].' % \
                info['error_blurb_']
            return _fill_page(info['error_page_'], info)
    else:
        info['details'] = 'Unexpected action trying to upload.'
        logging.error(info['details'])
        return _fill_page(info['error_page_'], info)
