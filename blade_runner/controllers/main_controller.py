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

import os
import sys
import socket
import logging
import plistlib
import subprocess
import tkMessageBox
import Tkinter as tk
import traceback as tb
import xml.etree.cElementTree as ET

blade_runner_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(blade_runner_dir, "dependencies"))
sys.path.insert(0, os.path.join(blade_runner_dir, "slack"))
sys.path.insert(0, blade_runner_dir)

from blade_runner.jamf_pro.jss_doc import JssDoc
from blade_runner.views.main_view import MainView
from blade_runner.user_actions import user_actions
from blade_runner.jamf_pro.computer import Computer
from blade_runner.jamf_pro.jss_server import JssServer
from blade_runner.windows.stall_window import StallWindow
from blade_runner.controllers.controller import Controller
from blade_runner.jamf_pro.params import SearchParams, VerifyParams
from blade_runner.controllers.search_controller import SearchController
from blade_runner.controllers.dual_verify_controller import DualVerifyController
from blade_runner.controllers.verification_controller import VerificationController
from blade_runner.dependencies.management_tools.slack import IncomingWebhooksSender as IWS


# TODO Interface with a Trello board and dynamically create lists for the DEP
# TODO BUG: If spaces are entered in the asset/barcode inputs the program quits.

logging.getLogger(__name__).addHandler(logging.NullHandler())


class MainController(Controller):
    """Blade Runner main controller."""

    def __init__(self, root, config_dir):
        """Initialize the main controller.

        Args:
            root: The root Tk window.
            config_dir (str): Path to the configuration directory. See Notes below.

        Notes:

            config_dir must contain the following directory structure with the accompanying configuration files,
            though the configuration file(s) shown in offboard_configs may have a different name.

            +---config_dir
            |   +---jamf_pro_configs
            |   |   /---jamf_pro.plist
            |   +---offboard_configs
            |   |   /---an_offboard_config
            |   |   /---another_offboard_config
            |   +---print_config
            |   |   /---print.plist
            |   +---python_bin_config
            |   |   /---python_bin.plist
            |   +---search_params_configs
            |   |   /---search_params.plist
            |   +---slack_configs
            |   |   /---slack.plist
            |   +---verify_params_configs
            |   |   /---verify_params.plist
            -------------

        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get logger.
        self.logger = logging.getLogger(__name__)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Initialize config paths
        self._config_dir = config_dir
        self._jamf_pro_config_path = os.path.join(config_dir, "jamf_pro_configs/jamf_pro.plist")
        self._slack_config_path = os.path.join(config_dir, "slack_configs/slack.plist")
        self._verify_config_path = os.path.join(config_dir, "verify_params_configs/verify_params.plist")
        self._search_config_path = os.path.join(config_dir, "search_params_configs/search_params.plist")
        self._print_config_path = os.path.join(config_dir, "print_config/print.plist")
        self._python_bin_config_path = os.path.join(config_dir, "python_bin_config/python_bin.plist")
        self._offboard_configs_dir = os.path.join(config_dir, "offboard_configs")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Check arg type. If it's a string, process as path and create dictionary, otherwise just save it.
        jss_server_data = plistlib.readPlist(self._jamf_pro_config_path)
        self._jss_server = JssServer(**jss_server_data)

        self._slack_data = plistlib.readPlist(self._slack_config_path)

        verify_params_data = plistlib.readPlist(self._verify_config_path)
        self.verify_params = VerifyParams(verify_params_data)

        search_params_data = plistlib.readPlist(self._search_config_path)
        self.search_params = SearchParams(search_params_data)

        self._doc_settings = plistlib.readPlist(self._print_config_path)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set report callback so that a Tk window will appear with the exception message when an exception occurs.
        self._root = root
        self._root.report_callback_exception = self._exception_messagebox
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Stores information about the computer
        self._computer = Computer()
        self._computer.serial_number = self._computer.get_serial()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Used to exit out of a function if the user cancels.
        self._proceed = True
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set views
        self._main_view = None
        self._entry_view = None
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set controllers
        self._search_controller = None
        self._verify_controller = None
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Initialize offboard config.
        self._offboard_config = None
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Save Verify/SearchParams original input
        self._verify_params_arg = verify_params_data
        self._search_params_arg = search_params_data
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set path to config directory that contains the configuration files.
        app_root_dir = os.path.abspath(__file__)
        for i in range(3):
            app_root_dir = os.path.dirname(app_root_dir)

        self.app_root_dir = app_root_dir
        # self._config_dir = os.path.join(self.app_root_dir, "config")
        self._blade_runner_dir = os.path.join(self.app_root_dir, "blade_runner")
        self._slack_dir = os.path.join(self._blade_runner_dir, "slack")
        # self._offboard_configs_dir = os.path.join(self._config_dir, "offboard_configs")
        self._secure_erase_dir = os.path.join(self._blade_runner_dir, "secure_erase")

    def reload_configs(self):
        """Reloads configuration files if the path to the config has been specified.

        Returns:
            void
        """
        if self._jamf_pro_config_path:
            jss_server_data = plistlib.readPlist(self._jamf_pro_config_path)
            self.logger.debug(jss_server_data)
            self._jss_server = JssServer(**jss_server_data)

        if self._slack_config_path:
            self._slack_data = plistlib.readPlist(self._slack_config_path)
            self.logger.debug(self._slack_data)

        if self._verify_config_path:
            verify_params_data = plistlib.readPlist(self._verify_config_path)
            self.logger.debug(verify_params_data)
            self.verify_params = VerifyParams(verify_params_data)

        if self._search_config_path:
            search_params_data = plistlib.readPlist(self._search_config_path)
            self.logger.debug(search_params_data)
            self.search_params = SearchParams(search_params_data)

        if self._print_config_path:
            self._doc_settings = plistlib.readPlist(self._print_config_path)
            self.logger.debug(self._doc_settings)

        self.logger.info("Reloaded configuration files.")

    def _exception_messagebox(self, exc, value, traceback):
        """Displays a message box with the accompanying exception message whenver an exception occurs.

        Args:
            exc: Exception received.
            value: Value of exception.
            traceback: Traceback from exception.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        try:
            # Grab the last value in the value tuple. This is normally the message.
            message = "{}".format(value[-1])
            # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
            # Display a message box containing the exception's message.
            tkMessageBox.showerror('Exception', message)
        except IndexError:
            tkMessageBox.showerror('Exception', value)
        finally:
            self.logger.error("".join(tb.format_exception(exc, value, traceback)))

    def run(self):
        """Start Blade-Runner.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create the main view.
        self._main_view = MainView(self._root, self)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set it to the middle of the screen.
        self._set_to_middle(self._main_view)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Refocus on the window.
        self.refocus()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Make this window the main loop.
        self._main_view.mainloop()

    def secure_erase(self):
        """Runs secure_erase.sh, which runs secure_erase_internals, in a new terminal window.

        Returns:
            void
        """
        subprocess.check_output(["open", "-n", "-a", "Terminal", os.path.join(self._secure_erase_dir, "secure_erase.sh")])

    def terminate(self):
        """Terminates Blade-Runner.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Destroy the main view and the root window.
        self._main_view.destroy()
        self._root.destroy()

    def restart(self):
        """Restart Blade-Runner without quiting the entire program.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create a new Computer object.
        self._computer = Computer()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create a new VerifyParams object.
        self.verify_params = VerifyParams(self._verify_params_arg)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create a new SearchParams object.
        self.search_params = SearchParams(self._search_params_arg)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("Blade-Runner reset.")

    def populate_config_combobox(self):
        """Populates the main view's combobox with available configuration files.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the XML config files from the config directory
        offboard_configs = self._get_offboard_configs(self._offboard_configs_dir)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Fill the main view's combobox with the XML files.
        self._main_view.combobox.config(values=offboard_configs)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set the initial choice to the first XML file in the list.
        self._main_view.combobox.current(0)

    def _get_offboard_configs(self, dir):
        """Gets the offboard XML configuration files from a given directory.

        Args:
            dir (str): Path to config directory.

        Returns:
            list: XML configuration files.
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get a list of the files in the config directory.
        files = os.listdir(dir)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get all XML files in the directory.
        offboard_configs = []
        for file in files:
            if file.endswith(".xml") and file[0] != "." and file[0] != "~":
                offboard_configs.append(file)
        return offboard_configs

    def save_offboard_config(self, offboard_config):
        """Save the offboard config as an XML string.

        Args:
            offboard_config (str): File name, not the file path.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Parse XML file into an XML tree.
        xml_file = os.path.join(self._offboard_configs_dir, offboard_config)
        xml_tree = ET.parse(xml_file)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the root of the tree.
        xml_root = xml_tree.getroot()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create offboard xml string and store it.
        self._offboard_config = ET.tostring(xml_root)

    def search_sequence(self, input_type):
        """Determines the search window sequence based on the input type and previous search params.

        Args:
            input_type (str): Data identifier.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Process the input type and handle the JSS search.
        self._main(input_type)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # For every search parameter enabled
        for param in self.search_params:
            # If search parameter hasn't been searched yet.
            if not self.search_params.was_searched(param):
                # If user hasn't canceled operation and no match was found
                if self._proceed is True and self._computer.jss_id is None:
                    # Process the input type and handle the JSS search.
                    self._main(param)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # All search params have been searched and Blade-Runner has finished processing the computer.
        # Restart Blade-Runner.
        self.restart()

    def _main(self, input_type):
        """Handles search events.

        Args:
            input_type (str): Data identifier.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Open the search view for the input type.
        self._open_search_view(input_type)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # If the user canceled the search view, proceed will be false, Blade-Runner will restart, and function returns.
        if self._proceed is False:
            self.restart()
            return
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Since the computer object has been filled with user input data for the input type, search the JSS.
        self._dynamic_search(self._computer, input_type)
        self.search_params.set_searched(input_type)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # If the search resulted in a match...
        if self._computer.jss_id:
            # Set match
            self.search_params.set_match(input_type)
            # Open view  so user can verify inputted data against JSS data.
            self._open_dual_verify_view()
            # If user didn't cancel operation...
            if self._proceed:
                # Get managed status of computer
                managed = self._jss_server.get_managed_status(self._computer.jss_id)
                self.logger.debug("Management status: {}".format(managed))
                # If managed status is false, re-enroll computer to set managed status to true. This enables the
                # JSS record to be modified
                if managed == 'false':
                    msg = "Enrolling to change managed status to true to enable modification of the Jamf Pro record."
                    self.logger.debug(msg)
                    # Open a stall window, enroll the computer, and close the stall window.
                    enroll_window = StallWindow(self._main_view, self._jss_server.enroll_computer, msg, process=True)
                    if not enroll_window.proceed:
                        return
            else:
                return
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Otherwise, if all input types have been searched...
        elif self.search_params.all_searched():
            # Open view  so user can verify inputted data.
            self._open_verify_view()
            # If user didn't cancel operation...
            if self._proceed:
                msg = "Enrolling because no Jamf Pro ID exists for this computer."
                self.logger.debug(msg)
                # Open a stall window, enroll the computer, and close the stall window.
                enroll_window = StallWindow(self._main_view, self._jss_server.enroll_computer, msg, process=True)
                if not enroll_window.proceed:
                    return
                # Since JSS ID has now been created, retrieve it.
                self._computer.jss_id = self._jss_server.match(self._computer.serial_number)
                self.logger.debug("Jamf Pro ID after enrolling: {}".format(self._computer.jss_id))
            else:
                return
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Otherwise, return.
        elif self._computer.jss_id is None:
            return
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Push computer's identity fields to the JSS.
        self._jss_server.push_identity_fields(self._computer)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Offboard computer
        self._offboard()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Send slack message and start slackify daemon according to slack data config.
        self._slack_handler(self._slack_data)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create and print JssDoc according to settings.
        self._jss_doc_handler(self._computer, self._jss_server, self._doc_settings)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("Blade Runner successfully finished.")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Display success message box.
        tkMessageBox.showinfo("Finished", "Blade-Runner successfully finished.")

    def _dynamic_search(self, computer, input_type):
        """Dynamically search the JSS with the Computer attribute that matches the input type.

        Args:
            computer (Computer): Stores information about the computer.
            input_type (str): Data identifier.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Use the computer object to set the search parameter.
        if input_type == "barcode_1":
            search_param = computer.barcode_1
        elif input_type == "barcode_2":
            search_param = computer.barcode_2
        elif input_type == "asset_tag":
            search_param = computer.asset_tag
        elif input_type == "serial_number":
            search_param = computer.serial_number
        else:
            raise SystemExit("The input type \"{}\" supplied from the button is not supported.".format(input_type))
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Search the JSS.
        computer.jss_id = self._jss_server.match(search_param)

    def _open_search_view(self, input_type):
        """Open the search view. Saves user input in computer object.

        Args:
            input_type (str): Data identifier.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # If serial number, save serial number to computer object. This allows the serial to be displayed before
        # submitting it for a search.
        if input_type == "serial_number":
            self._computer.serial_number = self._computer.get_serial()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Open the search controller/view. Inputs given to the view will be saved in the computer object.
        self._search_controller = SearchController(self._main_view, self._computer, input_type)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Wait for search view to close.
        self._main_view.wait_window(window=self._search_controller.entry_view)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # If the user canceled the operation, proceed will be false.
        self._proceed = self._search_controller.proceed

    def _open_verify_view(self):
        """Opens a VerifyView window.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self._verify_controller = VerificationController(self._main_view, self._computer, self.verify_params,
                                                         self.search_params)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Wait for entry view window to close.
        self._main_view.wait_window(window=self._verify_controller.entry_view)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # After entry view window has been closed through the "submit" button, proceed will be True, and the barcode,
        # asset, and name fields of the computer object will be updated.
        self._proceed = self._verify_controller.proceed

    def _open_dual_verify_view(self):
        """Opens a DualVerifyView window.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Open DualVerifyWindow/Controller
        self._verify_controller = DualVerifyController(self._main_view, self._computer, self.verify_params,
                                                       self._jss_server)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Wait for entry view window to close.
        self._main_view.wait_window(window=self._verify_controller.entry_view)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Store exit status of the view.
        self._proceed = self._verify_controller.proceed

    def _offboard(self):
        """Offboard computer object with the offboard config.

        Returns:

        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Update the JSS record according to the implementation of the user.
        user_actions.update_offboard_config(self)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Push the offboard config to the JSS to offboard the computer.
        self._jss_server.push_xml_str(self._offboard_config, self._computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the new managed status and make sure it's false
        post_managed_status = self._jss_server.get_managed_status(self._computer.jss_id)
        self.logger.debug("post_managed_status: {}".format(post_managed_status))
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Make sure managed status is false. If not, exit.
        if post_managed_status != 'false':
            msg = "Managed status was not false after offboarding. Aborting."
            self.logger.error(msg)
            self.restart()
            raise SystemError(msg)

    def _slack_handler(self, slack_data):
        """Handles all Slack related items: sends Slack message and starts Slackify daemon.

        Args:
            slack_data (dict): Slack configuration.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Notify slack channel that offboard tool has finished.
        if slack_data['slack_enabled'] == "True":
            message = slack_data['default_message']
            message = user_actions.update_slack_message(self, message)
            self.send_slack_message(message)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Start Slackify daemon
        if slack_data['slackify_daemon_enabled'] == 'True':
            self.logger.debug("Starting Slackify reminder daemon.")
            self.start_slackify_reminder_dameon()

    def _jss_doc_handler(self, computer, jss_server, doc_settings):
        """Creates a document from the predefined setup in JssDoc and prints the document
        to the default printer if print_doc is True.

        Args:
            computer (Computer): Stores information about the computer. Only used for JSS ID and "incorrect fields".
            jss_server (JssServer): JSS server to query.
            print_doc (bool): Prints document to default printer if True.

        Returns:

        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Prepare document for printing
        doc = JssDoc(jss_server, computer)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create html document from settings in JssDoc.
        doc.create_html()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Convert HTML document into a PDF document.
        doc.html_to_pdf()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # If document printing is enabled, print to the default printer.
        # if print_doc:
        #     doc.print_pdf_to_default()
        if doc_settings['print'].lower() == "true":
            doc.print_pdf_to_default()

    def send_slack_message(self, message):
        """Sends a Slack message to a specified channel and Slack url.

        Args:
            message (str): Message to be sent to the Slack channel.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the current IP
        current_ip = socket.gethostbyname(socket.gethostname())
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set up the Slack bot
        slack_bot = IWS(self._slack_data['slack_url'], bot_name=current_ip, channel=self._slack_data['slack_channel'])
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Send the Slack message
        slack_bot.send_message(message)

    def start_slackify_reminder_dameon(self):
        """Start the Slackify reminder daemon.

        Notes:
            The Slackify reminder daemon can't be imported into this script and run directly. In order for it to
            run as it's own detached process after this script finishes, it must be run through a subprocess call.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set up and run the command.
        cmd = ['/usr/bin/python', '-m', 'blade_runner.slack.slackify_reminder_daemon']
        subprocess.Popen(cmd, stderr=subprocess.STDOUT)

    def refocus(self):
        """Set the focus to the Python application.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set up the command
        select_window = ['/usr/bin/osascript', '-e',
                         'tell application "Finder" to set frontmost of process "Python" to true']
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        try:  # set focus to the main view.
            subprocess.check_output(select_window)
        except subprocess.CalledProcessError:
            self.logger.debug("Setting frontmost of process Python to true failed.")

    def open_config(self, config_id):
        """Opens the specified configuration file in its default application.

        Args:
            config_id (str): Denotes which path to use.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Determine the path to the configuration file.
        if config_id == "slack":
            path = self._slack_config_path
        elif config_id == "offboard":
            path = os.path.join(self._config_dir, "offboard_configs")
        elif config_id == "verify":
            path = self._verify_config_path
        elif config_id == "search":
            path = self._search_config_path
        elif config_id == "config":
            path = self._config_dir
        elif config_id == "print":
            path = self._print_config_path
        elif config_id == "python_bin":
            path = self._python_bin_config_path
        elif config_id == "jamf_pro":
            path = self._jamf_pro_config_path
        else:
            self.logger.warn("No configuration ID matches \"{}\"".format(config_id))
            raise SystemError("No configuration ID matches \"{}\"".format(config_id))
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Open the file in its default application
        if path:
            subprocess.check_output(["open", path])

    def cat_readme(self):
        """Outputs the text of README.md.

        Returns:
            Text of README.md.
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set the path to README.md.
        readme = os.path.join(self.app_root_dir, "README.md")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Read README.md contents and return them as a single string.
        with open(readme, "r") as f:
            return f.read()


def main():
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Ensure script is being run as root.
    if os.geteuid() != 0:
        raise SystemExit("Blade Runner must be run as root.")
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Set up logging values.
    fmt = '%(asctime)s %(process)d: %(levelname)8s: %(name)s.%(funcName)s: %(message)s'
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    log_dir = os.path.join(os.path.expanduser("~"), "Library/Logs/Blade Runner")
    filepath = os.path.join(log_dir, script_name + ".log")

    # Create directory for log if it DNE.
    try:
        os.mkdir(log_dir)
    except OSError as e:
        if e.errno != 17:
            raise e

    # Ensure that the owner is the logged in user.
    subprocess.check_output(['chown', '-R', os.getlogin(), log_dir])

    # Set up and get logger.
    logging.basicConfig(level=logging.DEBUG, format=fmt, filemode='a', filename=filepath)
    logger = logging.getLogger(script_name)
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Create main root window.
    root = tk.Tk()
    root.withdraw()
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Set up parent folder of config.
    abs_file_path = os.path.abspath(__file__)
    blade_runner_dir = abs_file_path
    for i in range(3):
        blade_runner_dir = os.path.dirname(blade_runner_dir)
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Path to configuration directory.
    config_dir = os.path.join(blade_runner_dir, "config")
    # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
    # Run the application
    app = MainController(root, config_dir)
    app.run()
    logger.info("Blade Runner exiting.")


if __name__ == "__main__":
    main()


