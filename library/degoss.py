#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

from ansible.module_utils.basic import *
from ansible.module_utils.six import integer_types, string_types

import json
import logging
import os
import six
import sys
import unittest
import yaml


if six.PY3:
    from io import StringIO
else:
    from StringIO import StringIO


CONSOLE_LOGGING_FORMAT = '[%(levelname)-8s] %(message)s'
DISK_LOGGING_FORMAT = '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s'

BOOLEAN_TRUE_MATCHER = re.compile(r'(true|yes|on)', re.I)


def main(argv=sys.argv):
    """Main entrypoint into the module, instantiates and executes the service."""
    Degoss(argv).execute()


class Degoss(object):

    def __init__(self, argv):
        """Constructor for a Degoss service."""
        # instantiate independent variables first
        self.argv = argv
        self.log_output = StringIO()

        # now that all independent variables are initialized, call initialization methods
        self.module = self.define_module()
        self.logger = self.setup_logging()

    def define_module(self):
        """Create the Ansible module definition and return it."""
        return AnsibleModule(
            argument_spec=dict(
                log_file=dict(required=False, default=None),
                verbose=dict(required=False, default=False),
            ),
            supports_check_mode=False,
        )

    def setup_logging(self):
        """Setup logging for the module based on parameters."""
        # configure output handlers
        buffer_handler = logging.StreamHandler(stream=self.log_output)
        buffer_handler.setFormatter(logging.Formatter(DISK_LOGGING_FORMAT)

        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setFormatter(logging.Formatter(CONSOLE_LOGGING_FORMAT))

        disk_handler = logging.FileHandler(filename=self.module.params.get('log_file', '/tmp/degoss.log'))
        disk_handler.setFormatter(logging.Formatter(DISK_LOGGING_FORMAT))

        logger = logging.getLogger('degoss')
        # catchall handler for saving output
        logger.addHandler(buffer_handler)

        if self.module.params.get('log_file', None):
            # conditionally setup disk logging
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

    def execute(self):
        """Execute the degoss process."""
        self.logger.debug("debug test")
        self.logger.info("info test")
        self.logger.warn("warn test")
        self.logger.error("error test")

        self.module.exit_json(changed=False, failed=False, output=self.log_output.getvalue())


class DegossTestCase(unittest.TestCase):
    pass


if __name__ == "__main__" and len(sys.argv) >= 2 and sys.argv[1] == "test":
    # allow executing test cases by running with 'test' as the first argument
    unittest.main(argv=[__name__], verbosity=2)
elif __name__ == "__main__":
    main()
