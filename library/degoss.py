#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

from ansible.module_utils.basic import *
from ansible.module_utils.six import integer_types, string_types

import json
import logging
import os
import platform
import six
import sys
import tempfile
import yaml


if six.PY3:
    from io import StringIO
    from urllib.request import Request, urlopen
else:
    from StringIO import StringIO
    from urllib2 import Request, urlopen


DOCUMENTATION = """
---
module: degoss
author: Naftuli Kay <me@naftuli.wtf>
short_description: Download, execute, and remove Goss against test cases.
description:
    - Download, execute, and remove Goss against test cases located on disk.
options:
    bin_dir:
        required: true
        description: The directory to install the Goss binary into.
    log_file:
        required: false
        description: If specifed, log module output to this file on disk on the remote host.
    verbose:
        required: false
        default: false
        description: If true, log output to standard error.
    version:
        required: false
        default: latest
        description: If latest, the latest available Goss version, otherwise the specified version, e.g. 0.3.6.
examples: []
"""


CONSOLE_LOGGING_FORMAT = '[%(levelname)-5s] %(message)s'
DISK_LOGGING_FORMAT = '%(asctime)s [%(levelname)-5s] %(name)s: %(message)s'

BOOLEAN_TRUE_MATCHER = re.compile(r'(true|yes|on)', re.I)


def main(argv=sys.argv):
    """Main entrypoint into the module, instantiates and executes the service."""
    Degoss(argv, AnsibleModule(
        argument_spec=dict(
            bin_dir=dict(required=True),
            log_file=dict(required=False, default=None),
            verbose=dict(required=False, default=False),
            version=dict(required=False, default='latest'),
        )
    )).execute()


class Degoss(object):

    def __init__(self, argv, module):
        """Constructor for a Degoss service."""
        # instantiate independent variables first
        self.argv = argv
        self.log_output = StringIO()
        self.module = module

        # now that all independent variables are initialized, call initialization methods
        self.logger = self.setup_logging()

        # arch/os detection
        self.os, self.arch = None, None
        self.detect_environment()

    def detect_environment(self):
        """Detect the runtime environment on the host."""
        uname = platform.uname()

        self.os, self.arch = uname[0].lower(), uname[4]

        if self.arch == 'x86_64':
            # goss publishes as goss-linux-amd64
            self.arch = 'amd64'
        elif self.arch == 'i386':
            # goss publishes as goss-linux-386
            self.arch = '386'

        self.logger.debug("Host environment is %s-%s", self.os, self.arch)


    def setup_logging(self):
        """Setup logging for the module based on parameters."""
        # rewrite warning to warn
        #  logging.addLevelName(30, 'WARN')

        # configure output handlers
        buffer_handler = logging.StreamHandler(stream=self.log_output)
        buffer_handler.setFormatter(logging.Formatter(CONSOLE_LOGGING_FORMAT))

        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setFormatter(logging.Formatter(CONSOLE_LOGGING_FORMAT))

        logger = logging.getLogger('degoss')

        # catchall handler for saving output
        logger.addHandler(buffer_handler)

        if self.module.params.get('log_file', None):
            # conditionally setup disk logging
            disk_handler = logging.FileHandler(filename=self.module.params.get('log_file'))
            disk_handler.setFormatter(logging.Formatter(DISK_LOGGING_FORMAT))

            logger.addHandler(disk_handler)

        if self.get_bool('verbose', False):
            # conditionally add stderr logging
            logger.addHandler(console_handler)

        logger.setLevel(logging.DEBUG)

        return logger

    def get_bool(self, name, default=False):
        """Get a booleanish parameter from the module parameters."""
        param = self.module.params.get(name, default)

        if param in (True, False):
            return param
        elif isinstance(param, str):
            return BOOLEAN_TRUE_MATCHER.search(param) is not None
        else:
            return False

    def get_release_url(self, version):
        """Fetch the Goss binary URL."""
        if version == 'latest':
            self.logger.debug("Goss version requested is latest, detecting the latest available Goss release"
                    " from GitHub.")

            status, url, response = self.request("https://github.com/aelsabbahy/goss/releases/latest")

            if status != 200:
                self.fail("Unable to determine latest Goss release, HTTP status %d".format(status))

            # url will be something like https://github.com/aelsabbahy/goss/releases/tag/v0.3.6,
            # we will extract the tag from this url, then attempt to transform this into a version
            tag = url.split('/')[-1]

            version = tag[1:] if tag[0] == 'v' else tag

            self.logger.info("Detected latest available Goss version as %s", version)

        # regardless, return the release URL
        return "https://github.com/aelsabbahy/goss/releases/download/v{}/goss-{}-{}".format(version, \
            self.os, self.arch)


    def request(self, url, method='GET'):
        """Make an HTTP request to the given URL and return the response."""

        r = Request(url)
        r.get_method = lambda: method

        response = urlopen(r)
        status, response_url = response.getcode(), response.geturl()

        return status, response_url, response

    def install(self):
        """Install the Goss binary."""
        bin_dir = self.module.params.get('bin_dir')
        release_url = self.get_release_url(self.module.params.get('version', 'latest'))

        self.logger.info("Installing the Goss binary from %s into %s", release_url, bin_dir)

        status, _, response = self.request(release_url)

        with open(os.path.join(bin_dir, 'goss'), 'w') as f:
            f.write(response.read())

        self.logger.debug("Successfully installed the binary to %s", os.path.join(bin_dir, 'goss'))


    def execute(self):
        """Execute the degoss process."""
        self.install()

        output_lines = [line for line in self.log_output.getvalue().split(os.linesep) if len(line) > 0]

        self.module.exit_json(changed=False, failed=False, output_lines=output_lines)

    def fail(self, message):
        """Fail with a message."""
        self.module.exit_json({ 'failed': True, 'msg': message})


if __name__ == "__main__":
    main()
