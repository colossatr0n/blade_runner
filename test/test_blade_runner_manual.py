#!/usr/bin/python

# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2019 University of Utah Student Computing Labs.
# All Rights Reserved.
#
# Author: Thackery Archuletta
# Creation Date: Oct 2018
# Last Updated: March 2019
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appears in all copies and
# that both that copyright notice and this permission notice appear
# in supporting documentation, and that the name of The University
# of Utah not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission. This software is supplied as is without expressed or
# implied warranties of any kind.
################################################################################

"""
How to run:

    sudo python test/test_blade_runner_manual.py

Current working directory must be Blade Runner, as in Contents/Resources/Blade\ Runner/.

"""

import os
import sys
import logging
import unittest
import subprocess
import Tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "blade_runner/dependencies"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "blade_runner/slack"))

from blade_runner.controllers.main_controller import MainController

logging.getLogger(__name__).addHandler(logging.NullHandler())


class TestBladeRunnerManual(unittest.TestCase):
    """Test the GUI and the server manually."""

    def setUp(self):
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create main root window.
        root = tk.Tk()
        root.withdraw()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get path to config folder
        abs_file_path = os.path.abspath(__file__)
        self.blade_runner_dir = os.path.dirname(abs_file_path)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.config_dir = os.path.join(self.blade_runner_dir, "config")

        # Set up main controller.
        self.br = MainController(root, self.config_dir)

    def test_manual(self):
        """Manually test Blade Runner."""
        self.br.run()


if __name__ == "__main__":
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Ensure run as root.
    if os.geteuid() != 0:
        raise SystemExit("Blade Runner must be run as root.")
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Set up logging vars.
    fmt = '%(asctime)s %(process)d: %(levelname)8s: %(name)s.%(funcName)s: %(message)s'
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    log_dir = os.path.join(os.path.expanduser("~"), "Library/Logs/Blade Runner")
    filepath = os.path.join(log_dir, script_name + ".log")

    # Create log path
    try:
        os.mkdir(log_dir)
    except OSError as e:
        if e.errno != 17:
            raise e

    # Ensure that the owner is the logged in user.
    subprocess.check_output(['chown', '-R', os.getlogin(), log_dir])

    # Set up logger.
    logging.basicConfig(level=logging.DEBUG, format=fmt, filemode='a', filename=filepath)
    logger = logging.getLogger(script_name)
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Start unit tests.
    unittest.main(verbosity=2)
