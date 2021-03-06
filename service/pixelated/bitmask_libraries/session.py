#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import errno
import traceback
import sys

import os
from leap.mail.imap.fetch import LeapIncomingMail
from leap.mail.imap.account import SoledadBackedAccount
from leap.mail.imap.memorystore import MemoryStore
from leap.mail.imap.soledadstore import SoledadStore
from pixelated.bitmask_libraries.config import LeapConfig
from pixelated.bitmask_libraries.provider import LeapProvider
from twisted.internet import reactor
from .nicknym import NickNym
from .auth import LeapAuthenticator, LeapCredentials
from .soledad import SoledadSessionFactory, SoledadSession
from .smtp import LeapSmtp


SESSIONS = {}


def open(username, password, server_name):
    try:
        certs_home = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", "..", "certificates"))

        config = LeapConfig(certs_home=certs_home)
        provider = LeapProvider(server_name, config)
        session = LeapSessionFactory(provider).create(LeapCredentials(username, password))

        return session
    except:
        raise


class LeapSession(object):
    """
    A LEAP session.


    Properties:

    - ``leap_config`` the configuration for this session (LeapClientConfig).

    - ``srp_session`` the secure remote password session to authenticate with LEAP. See http://en.wikipedia.org/wiki/Secure_Remote_Password_protocol (LeapSecureRemotePassword)

    - ``soledad_session`` the soledad session. See https://leap.se/soledad (LeapSecureRemotePassword)

    - ``nicknym`` the nicknym instance. See https://leap.se/nicknym (NickNym)

    - ``account`` the actual leap mail account. Implements Twisted imap4.IAccount and imap4.INamespacePresenter (SoledadBackedAccount)

    - ``incoming_mail_fetcher`` Background job for fetching incoming mails from LEAP server (LeapIncomingMail)
    """

    def __init__(self, provider, srp_session, soledad_session, nicknym, soledad_account, incoming_mail_fetcher):
        """
        Constructor.

        :param leap_config: The config for this LEAP session
        :type leap_config: LeapConfig

        """
        self.config = provider.config
        self.provider = provider
        self.srp_session = srp_session
        self.soledad_session = soledad_session
        self.nicknym = nicknym
        self.account = soledad_account
        self.incoming_mail_fetcher = incoming_mail_fetcher

        if self.config.start_background_jobs:
            self.start_background_jobs()

    def account_email(self):
        domain = self.provider.domain
        name = self.srp_session.user_name
        return '%s@%s' % (name, domain)

    def close(self):
        self.stop_background_jobs()

    def start_background_jobs(self):
        reactor.callFromThread(self.incoming_mail_fetcher.start_loop)

    def stop_background_jobs(self):
        reactor.callFromThread(self.incoming_mail_fetcher.stop)

    def sync(self):
        try:
            self.soledad_session.sync()
        except:
            traceback.print_exc(file=sys.stderr)
            raise


class LeapSessionFactory(object):
    def __init__(self, provider):
        self._provider = provider
        self._config = provider.config

    def create(self, credentials):
        key = self._session_key(credentials)
        session = self._lookup_session(key)
        if not session:
            session = self._create_new_session(credentials)
            self._remember_session(key, session)

        return session

    def _create_new_session(self, credentials):
        self._create_dir(self._provider.config.leap_home)
        self._provider.download_certificate_to('%s/ca.crt' % self._provider.config.leap_home)

        auth = LeapAuthenticator(self._provider).authenticate(credentials)
        soledad = SoledadSessionFactory.create(self._provider, auth, credentials.db_passphrase)

        nicknym = self._create_nicknym(auth, soledad)
        account = self._create_account(auth, soledad)
        incoming_mail_fetcher = self._create_incoming_mail_fetcher(nicknym, soledad,
                                                                   account, auth)

        smtp = LeapSmtp(self._provider, nicknym.keymanager, auth)
        smtp.start()

        return LeapSession(self._provider, auth, soledad, nicknym, account, incoming_mail_fetcher)

    def _lookup_session(self, key):
        global SESSIONS
        if key in SESSIONS:
            return SESSIONS[key]
        else:
            return None

    def _remember_session(self, key, session):
        global SESSIONS
        SESSIONS[key] = session

    def _session_key(self, credentials):
        return hash((self._provider, credentials.user_name))

    def _create_dir(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def _create_soledad_session(self, srp_session, db_passphrase):
        return SoledadSession(self._provider, db_passphrase, srp_session)

    def _create_nicknym(self, srp_session, soledad_session):
        return NickNym(self._provider, self._config, soledad_session, srp_session)

    def _create_account(self, srp_session, soledad_session):
        memstore = MemoryStore(permanent_store=SoledadStore(soledad_session.soledad))
        return SoledadBackedAccount(srp_session.uuid, soledad_session.soledad, memstore)

    def _create_incoming_mail_fetcher(self, nicknym, soledad_session, account, auth):
        return LeapIncomingMail(nicknym.keymanager, soledad_session.soledad, account,
                                self._config.fetch_interval_in_s, self._account_email(auth))

    def _account_email(self, auth):
        domain = self._provider.domain
        name = auth.user_name
        return '%s@%s' % (name, domain)
