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
import time
import multiprocessing
import logging
from test.support.integration import AppTestClient
from selenium import webdriver
import pixelated


def before_all(context):
    pixelated.controllers.features_controller.FeaturesController.DISABLED_FEATURES.append('autoRefresh')
    client = AppTestClient()
    context.client = client
    logging.disable('INFO')

    worker = lambda: client.app.run(host='localhost', port=4567, logFile=open('/tmp/behave-tests.log', 'w'))
    context._process = multiprocessing.Process(target=worker)
    context._process.start()

    # we must wait the server start listening
    time.sleep(1)


def after_all(context):
    context._process.terminate()


def before_feature(context, feature):
    # context.browser = webdriver.Firefox()
    context.browser = webdriver.PhantomJS()
    context.browser.set_window_size(1280, 1024)
    context.browser.implicitly_wait(5)
    context.browser.set_page_load_timeout(60)  # wait for data
    context.browser.get('http://localhost:4567/')


def after_feature(context, feature):
    context.browser.quit()


def take_screenshot(context):
    context.browser.save_screenshot('/tmp/screenshot.jpeg')


def save_source(context):
    with open('/tmp/source.html', 'w') as out:
        out.write(context.browser.page_source.encode('utf8'))
