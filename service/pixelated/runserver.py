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

import os
import sys
import logging
import json
from klein import Klein
from twisted.python.log import ILogObserver

klein_app = Klein()

import ConfigParser
from twisted.python import log
import sys
from leap.common.events import server as events_server
from pixelated.config import app_factory
import pixelated.config.args as input_args
import pixelated.bitmask_libraries.register as leap_register
from pixelated.bitmask_libraries.leap_srp import LeapAuthException
import pixelated.config.credentials_prompt as credentials_prompt
import pixelated.support.ext_protobuf  # monkey patch for protobuf in OSX
import pixelated.support.ext_sqlcipher  # monkey patch for sqlcipher in debian


app = Klein()
app.config = {}


def setup():
    args = input_args.parse()
    setup_debugger(args.debug)

    if args.register:
        register(*args.register[::-1])
    else:
        if args.dispatcher:
            config = fetch_credentials_from_dispatcher(args.dispatcher)
            app.config['LEAP_SERVER_NAME'] = config['leap_provider_hostname']
            app.config['LEAP_USERNAME'] = config['user']
            app.config['LEAP_PASSWORD'] = config['password']
        else:
            configuration_setup(args.config)
        start_services(args.host, args.port)


def register(username, server_name):
    try:
        leap_register.register_new_user(username, server_name)
    except LeapAuthException:
        print('User already exists')


def fetch_credentials_from_dispatcher(filename):
    if not os.path.exists(filename):
        print('The credentials pipe doesn\'t exist')
        sys.exit(1)
    with open(filename, 'r') as fifo:
        return json.loads(fifo.read())


def setup_debugger(enabled):
    debug_enabled = enabled or os.environ.get('DEBUG', False)
    log.startLogging(sys.stdout)

    if debug_enabled:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filename='/tmp/leap.log',
                            filemode='w')  # define a Handler which writes INFO messages or higher to the sys.stderr

        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

    return debug_enabled


def parse_config_from_file(config_file):
    config_parser = ConfigParser.ConfigParser()
    config_file = os.path.abspath(os.path.expanduser(config_file))
    config_parser.read(config_file)
    provider, user, password = \
        config_parser.get('pixelated', 'leap_server_name'), \
        config_parser.get('pixelated', 'leap_username'), \
        config_parser.get('pixelated', 'leap_password')

    # TODO: add error messages in case one of the parameters are empty
    return provider, user, password


def configuration_setup(config_file):
    provider, user, password = parse_config_from_file(config_file) if config_file else credentials_prompt.run()

    app.config['LEAP_SERVER_NAME'] = provider
    app.config['LEAP_USERNAME'] = user
    app.config['LEAP_PASSWORD'] = password


def start_services(bind_address, bind_port):
    events_server.ensure_server(port=8090)
    app_factory.create_app(app, bind_address, bind_port)


if __name__ == '__main__':
    setup()
