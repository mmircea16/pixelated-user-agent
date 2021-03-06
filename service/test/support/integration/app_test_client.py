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
import json
import shutil

from klein.test_resource import requestMock, _render
from leap.mail.imap.account import SoledadBackedAccount
from leap.soledad.client import Soledad
from mock import MagicMock, Mock
import os
from pixelated.adapter.draft_service import DraftService
from pixelated.adapter.mail_service import MailService
from pixelated.adapter.mailboxes import Mailboxes
from pixelated.adapter.soledad_querier import SoledadQuerier
from pixelated.adapter.tag_service import TagService
from pixelated.config import app_factory
from pixelated.controllers import FeaturesController, HomeController, MailsController, TagsController, \
    SyncInfoController, AttachmentsController
import pixelated.runserver
from pixelated.adapter.mail import PixelatedMail
from pixelated.adapter.search import SearchEngine
from test.support.integration.model import MailBuilder


class AppTestClient:
    def __init__(self, soledad_test_folder='soledad-test'):

        self.soledad = initialize_soledad(tempdir=soledad_test_folder)
        self.mail_address = "test@pixelated.org"

        # setup app
        PixelatedMail.from_email_address = self.mail_address

        SearchEngine.INDEX_FOLDER = soledad_test_folder + '/search_index'

        self.app = pixelated.runserver.app

        self.soledad_querier = SoledadQuerier(self.soledad)
        self.soledad_querier.get_index_masterkey = lambda: '_yg2oG_5ELM8_-sQYcsxI37WesI0dOtZQXpwAqjvhR4='

        self.account = SoledadBackedAccount('test', self.soledad, MagicMock())
        self.mailboxes = Mailboxes(self.account, self.soledad_querier)
        self.mail_sender = Mock()
        self.tag_service = TagService()
        self.draft_service = DraftService(self.mailboxes)
        self.mail_service = MailService(self.mailboxes, self.mail_sender, self.tag_service,
                                        self.soledad_querier)
        self.search_engine = SearchEngine(self.soledad_querier)
        self.search_engine.index_mails(self.mail_service.all_mails())

        features_controller = FeaturesController()
        features_controller.DISABLED_FEATURES.append('autoReload')
        home_controller = HomeController()
        mails_controller = MailsController(mail_service=self.mail_service,
                                           draft_service=self.draft_service,
                                           search_engine=self.search_engine)
        tags_controller = TagsController(search_engine=self.search_engine)
        sync_info_controller = SyncInfoController()
        attachments_controller = AttachmentsController(self.soledad_querier)

        app_factory._setup_routes(self.app, home_controller, mails_controller, tags_controller,
                                  features_controller, sync_info_controller, attachments_controller)

    def _render(self, request, as_json=True):
        def get_request_written_data(_=None):
            written_data = request.getWrittenData()
            if written_data:
                return json.loads(written_data) if as_json else written_data

        d = _render(self.app.resource(), request)
        if request.finished:
            return get_request_written_data(), request
        else:
            d.addCallback(get_request_written_data)
            return d, request

    def get(self, path, get_args, as_json=True):
        request = requestMock(path)
        request.args = get_args
        return self._render(request, as_json)

    def post(self, path, body=''):
        request = requestMock(path=path, method="POST", body=body, headers={'Content-Type': ['application/json']})
        return self._render(request)

    def put(self, path, body):
        request = requestMock(path=path, method="PUT", body=body, headers={'Content-Type': ['application/json']})
        return self._render(request)

    def delete(self, path):
        request = requestMock(path=path, method="DELETE")
        return self._render(request)

    def add_document_to_soledad(self, _dict):
        self.soledad_querier.soledad.create_doc(_dict)

    def add_mail_to_inbox(self, input_mail):
        mail = self.mailboxes.inbox().add(input_mail)
        mail.update_tags(input_mail.tags)
        self.search_engine.index_mail(mail)

    def add_multiple_to_mailbox(self, num, mailbox='', flags=[], tags=[]):
        mails = []
        for _ in range(num):
            input_mail = MailBuilder().with_status(flags).with_tags(tags).build_input_mail()
            mail = self.mailboxes._create_or_get(mailbox).add(input_mail)
            mails.append(mail)
            mail.update_tags(input_mail.tags)
            self.search_engine.index_mail(mail)
        return mails


def initialize_soledad(tempdir):
    if os.path.isdir(tempdir):
        shutil.rmtree(tempdir)

    uuid = "foobar-uuid"
    passphrase = u"verysecretpassphrase"
    secret_path = os.path.join(tempdir, "secret.gpg")
    local_db_path = os.path.join(tempdir, "soledad.u1db")
    server_url = "http://provider"
    cert_file = ""

    class MockSharedDB(object):
        get_doc = Mock(return_value=None)
        put_doc = Mock()
        lock = Mock(return_value=('atoken', 300))
        unlock = Mock(return_value=True)
        close = Mock()

        def __call__(self):
            return self

    Soledad._shared_db = MockSharedDB()

    _soledad = Soledad(
        uuid,
        passphrase,
        secret_path,
        local_db_path,
        server_url,
        cert_file)
    return _soledad
