Welcome to KBasix

Introduction

   This  is  the  KBasix CMS system. It provides basic authentication and
   file-management capabilities, together with a simple set of ACL controls. It
   also supports mathematical notation via MathJax:

   $$e^{i \pi} + 1 = 0$$

Basic features

     * Internal authentication (LDAP too)
     * File uploads, with quotas
     * Flexible, human-readable metadata
     * Supports user and group ACLs (read-only)
     * Does not use cookies
     * Javascript is optional (but needed for MathJax)
     * File-based database
     * Command-line backend
     * Written in Python
     * BSD license

Requirements

     * RHEL 6 or CentOS 6 (tested under Red Hat Enterprise Linux)
     * An Apache webserver
     * The following modules: mod_python and mod_ssl
     * The Python programming language

Download

   Two packages are offered, with and without MathJax:

     * KBasix w/MathJax (7.6MB)
       https://www.math.utoronto.ca/marco/kbasix_m.tbz2

     * KBasix (61KB)
       https://www.math.utoronto.ca/marco/kbasix.tbz2

Installation

   Note: KBasix is BETA software, it's currently being tested and developed.
   Use   at   your  own  risk!  Bug  and  security  reports  welcomed  at
   marco@math.utoronto.ca.

   Extracting the downloaded bundle by means of tar -jxvf kbasix_m.tbz2 yields
   the following file hierarchy:

        kbasix
          |-files
          |   |_shared
          |       |_local
          |-logs
          |-sys
          |_web
             |-cms
             |-MathJax
             |_users

   (don't forget to do chown -R webuser:webgroup kbasix, where webuser and
   webgroup are the user and group Apache runs as). This example shows the
   contents of the MathJax bundle, but it's optional and can be disabled from
   defs.py.

   All user-uploaded files are stored in files, and logs is self-explanatory.
   The sys directory contains the user and group information files in JSON
   format. None of these should be directly accessible through the web server.
   The  web  directory, on the other hand, should be made DocumentRoot in
   httpd.conf (e.g. DocumentRoot /www/kbasix/web). Furthermore, the following
   two directives should be set: Options SymLinksifOwnerMatch and AllowOverride
   All. KBasix proper is stored in cms. Files which the users have shared with
   the world are symlinked within subdirectories inside users so that, for
   example,    user   "Sora"   can   make   her   files   accessible   at
   https://www.mykbsite.org/users/Sora  (assuming  the  site is hosted at
   www.mykbsite.org).

   You can now configure KBasix by editing the defs.py file inside cms (make
   sure  not to leave any backup files behind e.g. defs.py~). The file is
   documented,  but  in  the  simplest  case suffice to set the variables
   kbasix_root_ and kbasix_url_ near the top of the defintions to their proper
   values (in this example they'd be /www/kbasix and https://www.mykbsite.org,
   respectively).

   Finally, edit the CSS/HTML files to taste (probably not needed for now). For
   extra security it's a good idea to narrow permissions and make some files
   and directories immutable. Running the following (as root) is recommended:

       zsh -f
       chmod 600 kbasix/**/*(.)
       chmod 600 kbasix/**/.htaccess
       chmod 700 kbasix/**/*(/)
       chmod 700 kbasix
       chattr +i kbasix/**/.htaccess
       chattr +i kbasix/web/*(.)
       chattr +i kbasix/web
       chattr -R +i kbasix/web/cms
       chattr +i kbasix

   To access the CMS make sure the Apache web server is up and running. KBasix
   will only work through an encrypted connection, so having an SSL certificate
   is nice (but not required). What is important is that the ssl.conf file be
   properly  configured.  Assuming  that's been done, and that the URL is
   https://www.mykbsite.org, it is now necessary to configure python.conf as
   follows:

        <Directory /www/kbasix/web>
          AddHandler python-program .py
          PythonHandler mod_python.publisher
          PythonDebug Off
        </Directory>

   (to aid debugging on a non-production server one can set PythonDebug On).
   Restart  Apache  and  if  all goes well KBasix should be reachable at:
   https://www.mykbsite.org

   Run tail -F on the KBasix log in the logs directory to keep track of what's
   going on. The default level in defs.py is debug. Click on the Register
   button at the top of the CMS to create a KBasix account.

KBasix Manual

   There isn't a user or administrator guide (yet). Overall configuration is
   done by editing defs.py (which is fairly well documented). The entire KBasix
   CMS can easily be relocated by simply moving the kbasix/ hierarchy (and
   changing the kbasix_root_ and kbasix_url_ settings in defs.py). A KBasix
   installation can be backed up with a simple tar or rsync of kbasix/.

   KBasix has no concept of an administrator at the GUI level (although one can
   certainly be written). Low-level administration is through the command line.
   To  use  it,  cd  into  kbasix/web/cms  and  run  python. The two main
   administration modules are manage_users and manage_kbasix. A brief sample
   session is as follows:

     # whoami
     webuser
     # pwd
     /www/kbasix/web/cms
     # python
     Python 2.6.6 (r266:84292, May  1 2012, 13:52:17)
     [GCC 4.4.6 20110731 (Red Hat 4.4.6-3)] on linux2
     Type "help", "copyright", "credits" or "license" for more information.
     >>> import manage_users
     >>> import manage_kbasix
     >>> manage_users._finger()
     [u'acky', u'nana', u'sora', u'yuma']
     >>> manage_kbasix._finger('yuma')
     {u'last_login': 1345738231.8814499,
      u'login_name': u'yuma',
      u'quota': 1048576,
      u'registered': 1344365184.5450959,
      u'user_email': u'yuma-a@hello.av.jp',
      u'user_name': u'YumA'}
     >>> print(manage_users._mod.__doc__)
     Modify a user or a group.

            (OK, status) = _mod(name, settings, is_type='account')

         'name' is either a login or group name. The 'is_type' parameter can
         be 'account' or 'group'. User/group properties are modified via the
         'settings' dictionary, the keys of which correspond to those from
         the '_user_add'/'_group_add' functions (unknown keys are ignored).
         Return is (bool, str).

     >>>

   Notable functions available from manage_users are:

       _user_add
       _authenticate
       _group_add
       _del
       _mod
       _info
       _finger

   And from manage_kbasix:

      _account_add
      _account_mod
      _account_del
      _account_info
      _finger

   Information about these functions can be easily obtained by via .__doc__.
   KBasix is offered with icons by Mark James.
