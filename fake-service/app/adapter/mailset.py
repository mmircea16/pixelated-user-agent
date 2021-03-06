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
from mail import Mail


class MailSet:

    def __init__(self):
        self.ident = 0
        self.mails = {}

    def add(self, mbox_mail):
        self.mails[self.ident] = Mail(mbox_mail, self.ident)
        self.ident += 1

    def values(self):
        return self.mails.values()

    def get(self, mail_id):
        return self.mails.get(mail_id)

    def mark_as_read(self, mail_id):
        mail = self.get(mail_id)
        mail.status.append('read')

    def delete(self, mail_id):
        """
        Returns True if the email got purged,
        else returns False meaning the email got moved to trash
        """

        mail = self.get(mail_id)
        if 'trash' in mail.tags:
            del self.mails[mail_id]
            return True
        mail.tags.append('trash')
        return False

    def update(self, mail):
        self.mails[mail.ident] = mail

    def add_draft(self, mail):
        mail.ident = self.ident
        self.mails[mail.ident] = mail
        self.ident += 1
        return mail

    def find(self, draft_reply_for):
        match = [
            mail
            for mail in self.mails.values
            () if mail.draft_reply_for == draft_reply_for]
        if len(match) == 0:
            return None
        else:
            return match[0]
