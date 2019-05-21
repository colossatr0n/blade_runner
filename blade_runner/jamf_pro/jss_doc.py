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
import logging

from blade_runner.document import document as doc
from blade_runner.user_actions import user_actions

logging.getLogger(__name__).addHandler(logging.NullHandler())


class JssDoc(object):
    """Creates a document by querying the JSS for a given computer and by using the "incorrect" fields stored
    in Computer."""

    def __init__(self, jss_server, computer, filename="barcode_1"):
        """Initialize JssDoc.

        Args:
            jss_server (JssServer): JSS server to query.
            computer (Computer): Contains information about the computer.
            filename (str): Indicates how the file will be named.
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger = logging.getLogger(__name__)
        # Set computer and server.
        self.jss_server = jss_server
        self.computer = computer
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get path to Python script.
        blade_runner_dir = os.path.abspath(__file__)
        for i in range(3):
            blade_runner_dir = os.path.dirname(blade_runner_dir)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set path to docs generated by JssDoc.
        home_dir = os.path.expanduser("~")
        documents_dir = os.path.join(home_dir, "Documents")
        br_docs_dir = os.path.join(documents_dir, "Blade Runner")
        self.jamf_pro_docs = os.path.join(br_docs_dir, "Jamf Pro Docs")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set the basename of the output file without an extension
        if filename == "barcode_1":
            lbasename = self.jss_server.get_barcode_1(self.computer.jss_id) + "_barcode_1"
        elif filename == "barcode_2":
            lbasename = self.jss_server.get_barcode_2(self.computer.jss_id) + "_barcode_2"
        elif filename == "asset_tag":
            lbasename = self.jss_server.get_asset_tag(self.computer.jss_id) + "_asset"
        elif filename == "serial_number":
            lbasename = self.jss_server.get_serial(self.computer.jss_id) + "_serial"
        elif filename == "name":
            lbasename = self.jss_server.get_name(self.computer.jss_id) + "_name"
        else:
            lbasename = ""
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set the absolute path to the generated file without an extension
        self.pre_ext = os.path.join(self.jamf_pro_docs, lbasename)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Append the extensions
        self.html_doc = "{}.html".format(self.pre_ext)
        self.pdf_doc = "{}.pdf".format(self.pre_ext)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Set the HTML font size
        self.font_size = 5

    def _build_html(self):
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the name from the previous computer name extension attribute.
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the name of the computer.
        name = self.jss_server.get_name(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the barcode of the computer.
        barcode_1 = self.jss_server.get_barcode_1(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the barcode of the computer.
        barcode_2 = self.jss_server.get_barcode_2(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get the computer's asset tag.
        asset_tag = self.jss_server.get_asset_tag(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get computer's drive capacity
        drive_capacity = self.jss_server.get_drive_capacity(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get computer model.
        computer_model = self.jss_server.get_model(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get SSD status.
        if "SSD" in computer_model or "OWC" in computer_model:
            has_ssd = "Yes"
        else:
            has_ssd = "No"
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Gets computer's total RAM
        ram_total = self.jss_server.get_ram(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get managed status.
        managed = self.jss_server.get_managed_status(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Get serial number.
        serial_number = self.jss_server.get_serial(self.computer.jss_id)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Lambda expression for filtering out None and replacing it with "".
        none_filter = lambda x : "" if x is None else x
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Build review HTML string.
        review = False
        # Review content string will be built and used only if one of the "incorrect" fields is not None.
        review_content = """<b>Review these to fix any Jamf Pro inconsistencies.</b>"""
        # Check if any field needs to be reviewed.
        if self.computer.incorrect_barcode_1:
            review = True
            review_content += """
            <p>
            <b>Previous barcode 1: </b> <font color="red">{0}</font>
            """.format(none_filter(self.computer.incorrect_barcode_1))
        if self.computer.incorrect_barcode_2:
            review = True
            review_content += """
            <p>
            <b>Previous barcode 2: </b> <font color="red">{0}</font>
            """.format(none_filter(self.computer.incorrect_barcode_2))
        if self.computer.incorrect_asset:
            review = True
            review_content += """
            <p>
            <b>Previous asset tag: </b> <font color="red">{0}</font>
            """.format(none_filter(self.computer.incorrect_asset))
        if self.computer.incorrect_serial:
            review = True
            review_content += """
            <p>
            <b>Previous serial: </b> <font color="red">{0}</font>
            """.format(none_filter(self.computer.incorrect_serial))
        # If there's nothing to review, set review_content to empty string.
        if not review:
            review_content = ""
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Build HTML string
        start_content = """
         <!DOCTYPE HTML PUBLIC " -//W3C//DTD HTML 4.01 Transition//EN"
         "http://www.w3.org/TR/htm14/loose.dtd">
         <html>
           <head>
             <title>Inventory</title>
             <link rel="stylesheet" href="myCs325Style.css" type="text/css"/>
           </head>
           <body>
             <font size=\"""" + str(self.font_size) + """\">
         """

        items = [("Name", name),
                ("Barcode 1", barcode_1),
                ("Barcode 2", barcode_2),
                ("Asset Tag", asset_tag),
                ("Jamf ID", self.computer.jss_id, "Managed", managed),
                ("Serial Number", serial_number),
                ("Model", computer_model),
                ("SSD", has_ssd, "RAM", ram_total),
                ("Storage", drive_capacity)]

        user_actions.modify_items(self, items)
        mid_content = self._build_data(items)

        end_content = review_content + """
             </font>
           </body>
         </html>"""

        file_content = start_content + mid_content + end_content
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>

        return file_content

    def _build_data(self, items):
        data_content = ""
        for pair in items:
            for i, val in enumerate(pair):
                if i > 2:
                    data_content += " &nbsp;&nbsp; "

                if i % 2 == 1:
                    data_content += "<b>" + str(pair[i - 1]) + ": </b> " + str(pair[i])

            data_content += "\n<p>\n"

        return data_content

    def create_html(self):
        """Creates an .html JSS document.

        Returns:
            void
        """
        file_content = self._build_html()
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Make directory for the generated JSS document if it doesn't exist.
        try:
            os.makedirs(self.jamf_pro_docs)
        except OSError as e:
            # Errno 17 is "Directory exists".
            if e.errno != 17:
                raise
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Create HTML document.
        doc.create_html(file_content, self.html_doc)

    def open_html(self):
        """Open the html file in Safari.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("open_html: started")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        doc.open_html(self.html_doc)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("open_html: finished")

    def html_to_pdf(self):
        """Convert HTML file to PDF. Prints only the first page, which is the "-P 1" option.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("Converting HTML to PDF")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        doc.html_to_pdf(self.html_doc)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("Converting HTML to PDF finished.")

    def print_pdf_to_default(self):
        """Print PDF file to default printer.

        Returns:
            void
        """
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("print_pdf_to_default: started")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        doc.print_pdf_to_default(self.pdf_doc)
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        self.logger.info("print_pdf_to_default: finished")
