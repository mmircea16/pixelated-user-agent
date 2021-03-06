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
import unittest

from mockito import *
from pixelated.adapter.mailbox import Mailbox
from pixelated.adapter.mailboxes import Mailboxes


class PixelatedMailboxesTest(unittest.TestCase):
    def setUp(self):

        self.querier = mock()
        self.account = mock()
        self.account.mailboxes = []
        self.drafts_mailbox = mock()
        self.drafts_mailbox.mailbox_name = 'drafts'
        self.mailboxes = Mailboxes(self.account, self.querier)
        self.mailboxes.drafts = lambda: self.drafts_mailbox

    def test_search_for_tags(self):
        mailbox = mock()
        self.mailboxes.mailboxes = lambda: [mailbox]

        tags_to_search_for = {'tags': ['inbox', 'custom_tag']}

        when(Mailbox).create('INBOX', self.querier).thenReturn(mailbox)
        when(mailbox).mails_by_tags(any(list)).thenReturn(["mail"])

        mails = self.mailboxes.mails_by_tag(tags_to_search_for['tags'])

        self.assertEqual(1, len(mails))
        self.assertEqual("mail", mails[0])
