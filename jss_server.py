#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import subprocess
from management_tools import loggers
import urllib2
import xml.etree.cElementTree as ET
import base64
import json
import re
import inspect


class JssServer(object):
    def __init__(self, username=None, password=None, jss_url=None, invite=None):
        self.username = username
        self.password = password
        self.jss_url = jss_url
        self.invite = invite
        self.search_param = None

    def match(self, search_param):

        # Using the JSS API go to the server and pull down the computer id.
        '''Potential fix. If the serial number contains a forward slash, the url request fails. Tried using %2F to fix
        the problem but that didn't work. This is a problem when enrolling VMs, unless you change the VM serial. ???
        Here's an example of what doesn't work:

            string = urllib.quote_plus('VM3Z3gnZu/1a')
            computer_url = '***REMOVED***/JSSResource/computers/match/' + string
        '''
        computer_url = self.jss_url + '/JSSResource/computers/match/' + search_param

        request = urllib2.Request(computer_url)
        request.add_header('Accept', 'application/json')
        request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            err = "{0}: JSS server could not be reached.".format(e)
            logger.error(err)
            raise SystemExit(err)
        except urllib2.URLError as e:
            err = "{0}: No network connection detected.".format(e)
            logger.error(err)
            raise SystemExit(err)

        logger.info("Status code from request: %s" % response.code)
        response_json = json.loads(response.read())

        # Splits the computer match from the xml to be read below.
        # The UDID matches to one computer. Store the computer information into a new xml.
        try:
            split_computer_match = response_json['computers'][0]
        except:
            if len(search_param) > 10:
                logger.info("Serial number was not found in the JSS.")
            else:
                logger.info("Barcode or asset not found in the JSS.")
            return None
        # Prints the computers ID.
        logger.info("JSS assigned ID: %r" % split_computer_match['id'])
        computer_id = split_computer_match['id']
        return str(computer_id)

    def get_hardware_inventory(self, computer_id):

        # Using the JSS API go to the server and pull down the computer id.

        computer_url = self.jss_url + '/JSSResource/computers/id/' + computer_id + '/subset/Hardware'

        request = urllib2.Request(computer_url)
        request.add_header('Accept', 'application/json')
        request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))

        response = urllib2.urlopen(request)
        logger.info("Status code from request: %s" % response.code)
        response_json = json.loads(response.read())

        hardware_list_main = response_json['computer']['hardware']
        # print hardware_list_main
        return hardware_list_main

    def get_general_inventory(self, computer_id):

        # Using the JSS API go to the server and pull down the computer id.

        computer_url = self.jss_url + '/JSSResource/computers/id/' + computer_id + '/subset/General'

        request = urllib2.Request(computer_url)
        request.add_header('Accept', 'application/json')
        request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))

        response = urllib2.urlopen(request)
        logger.info("Status code from request: %s" % response.code)
        response_json = json.loads(response.read())

        general_list_main = response_json['computer']['general']

        return (general_list_main)

    def get_extension_attributes(self, jss_id):
        logger.debug("jss_url: {}".format(self.jss_url))
        logger.debug("jss_id: {}".format(jss_id))
        # api request url
        computer_url = self.jss_url + '/JSSResource/computers/id/' + jss_id + '/subset/extension_attributes'

        # executing/sending request
        request = urllib2.Request(computer_url)
        request.add_header('Accept', 'application/json')

        # providing credentials
        request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))

        # receiving response of request
        response = urllib2.urlopen(request)

        logger.info("Status code from request: %s" % response.code)
        # putting response in JSON format
        response_json = json.loads(response.read())

        # remove unicode
        # response_json = ast.literal_eval(json.dumps(response_json))

        jss_extension_attributes = response_json.get('computer', {}).get('extension_attributes', {})

        return jss_extension_attributes

    def get_location_fields(self, computer_id):

        computer_url = self.jss_url + '/JSSResource/computers/id/' + computer_id + '/subset/Location'

        request = urllib2.Request(computer_url)

        request.add_header('Accept', 'application/json')
        request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))

        # receiving response of request
        response = urllib2.urlopen(request)

        # putting response in JSON format
        response_json = json.loads(response.read())

        jss_location_fields = response_json.get('computer', {}).get('location', {})

        return jss_location_fields

    def get_prev_name(self, jss_id):
        jss_extension_attributes = self.get_extension_attributes(jss_id)

        # store tugboat extension attributes
        for attribute in jss_extension_attributes:

            if attribute['name'] == 'Previous Computer Names':
                prev_name = attribute['value']
                return prev_name

        return ""

    def delete_record(self, computer_id):
        self._delete_handler(computer_id)

    def get_tugboat_fields(self, computer_id):
        # get jss extenstion attributes
        jss_extension_attributes = self.get_extension_attributes(computer_id)

        # store tugboat extension attributes
        for attribute in jss_extension_attributes:

            if attribute['name'] == 'Onboarding IP':

                onboarding_IP = attribute['value']

            elif attribute['name'] == 'Inventory Status':

                inventory_status = attribute['value']

            elif attribute['name'] == 'Inventory Category':

                inventory_category = attribute['value']

            elif attribute['name'] == 'Budget Source':

                budget_source = attribute['value']

        tugboat_ext_attr = {'extension_attributes'.decode('utf-8'): {}}
        tugboat_ext_attr['extension_attributes'].update({'Onboarding IP'.decode('utf-8'): onboarding_IP,
                                                         'Inventory Status'.decode('utf-8'): inventory_status,
                                                         'Inventory Category'.decode('utf-8'): inventory_category,
                                                         'Budget Source'.decode('utf-8'): budget_source})

        # get jss location fields such as building, department, email, phone, realname, etc.
        jss_location_fields = self.get_location_fields(computer_id)
        tugboat_loc_fields = {'location'.decode('utf-8'): {}}

        # store tugboat location fields and reset user
        building = jss_location_fields['building']
        department = jss_location_fields['department']
        email_address = jss_location_fields['email_address']
        phone = jss_location_fields['phone']
        phone_number = jss_location_fields['phone_number']
        position = jss_location_fields['position']
        real_name = jss_location_fields['real_name']
        realname = jss_location_fields['realname']
        room = jss_location_fields['room']
        username = jss_location_fields['username']

        tugboat_loc_fields['location'].update({'building'.decode('utf-8'): building,
                                               'department'.decode('utf-8'): department,
                                               'email_address'.decode('utf-8'): email_address,
                                               'phone'.decode('utf-8'): phone,
                                               'phone_number'.decode('utf-8'): phone_number,
                                               'position'.decode('utf-8'): position,
                                               'real_name'.decode('utf-8'): real_name,
                                               'realname'.decode('utf-8'): realname,
                                               'room'.decode('utf-8'): room,
                                               'username'.decode('utf-8'): username})

        # Get general inventory to get managed status and serial number
        jss_general_inventory = self.get_general_inventory(computer_id)
        computer_name = jss_general_inventory['name']
        serial_number = jss_general_inventory['serial_number']
        barcode_number_jss = jss_general_inventory['barcode_1']
        yellow_asset_tag_jss = jss_general_inventory['asset_tag']

        # Get managed status
        managed = str(jss_general_inventory['remote_management']['managed'])

        tugboat_gen_inventory = {'general'.decode('utf-8'): {}}
        # Update general inventory tugboat dictionary
        tugboat_gen_inventory['general'].update({'computer_name'.decode('utf-8'): computer_name,
                                                 'serial_number'.decode('utf-8'): serial_number,
                                                 'remote_management'.decode('utf-8'): {},
                                                 'barcode_1'.decode('utf-8'): barcode_number_jss,
                                                 'asset_tag'.decode('utf-8'): yellow_asset_tag_jss})

        tugboat_gen_inventory['general']['remote_management'].update(
            {'managed'.decode('utf-8'): managed.decode('utf-8')})

        # tugboat_fields = {'computer': None}
        tugboat_fields = {}
        tugboat_fields.update(tugboat_loc_fields)
        tugboat_fields.update(tugboat_gen_inventory)
        tugboat_fields.update(tugboat_ext_attr)

        return tugboat_fields

    def get_offboard_fields(self, computer_id):

        offboard_fields = self.get_tugboat_fields(computer_id)
        offboard_fields['extension_attributes'].pop('Budget Source', None)
        offboard_fields['general'].pop('barcode_1', None)
        offboard_fields['general'].pop('asset_tag', None)

        return offboard_fields

    def push_enroll_fields(self, computer, budget_source=None):
        '''Pushes the following to the JSS:
            barcode number
            yellow asset tag number
            budget source
        '''
        logger.info("push_enroll_fields(): activated")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # v BEGIN: Create XML structure that will be sent through the api call
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Computer: Top XML tag
        top = ET.Element('computer')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Extension attributes tag
        ext_attrs = ET.SubElement(top, 'extension_attributes')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        if budget_source is not None:
            budget_source.decode('utf-8')
            # Extension attribute tag
            budget_source_attr = ET.SubElement(ext_attrs, 'extension_attribute')

            # ID tag for budget source
            budget_source_id = ET.SubElement(budget_source_attr, 'id')
            budget_source_id.text = '22'

            # Name tag for budget source
            budget_source_name = ET.SubElement(budget_source_attr, 'name')
            budget_source_name.text = 'Budget Source'

            # Value tag for budget source
            budget_source_value = ET.SubElement(budget_source_attr, 'value')
            budget_source_value.text = budget_source
            # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        if computer.name is not None:
            # Extension attribute tag
            previous_computer_names__attr = ET.SubElement(ext_attrs, 'extension_attribute')

            # ID tag for previous computer name
            previous_computer_names_id = ET.SubElement(previous_computer_names__attr, 'id')
            previous_computer_names_id.text = '46'

            # Name tag for previous computer names
            previous_computer_names_name = ET.SubElement(previous_computer_names__attr, 'name')
            previous_computer_names_name.text = 'Previous Computer Names'

            # Value tag for budget source
            previous_computer_names_value = ET.SubElement(previous_computer_names__attr, 'value')
            previous_computer_names_value.text = computer.name

        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # General tag
        general = ET.SubElement(top, 'general')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # barcode_1 tag (white tag)
        if computer.barcode is not None:
            barcode_1_xml = ET.SubElement(general, 'barcode_1')
            barcode_1_xml.text = computer.barcode.decode('utf-8')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # asset_tag tag (yellow tag)
        if computer.asset is not None:
            asset_tag_xml = ET.SubElement(general, 'asset_tag')
            asset_tag_xml.text = computer.asset.decode('utf-8')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        if computer.serial is not None:
            serial_number_xml = ET.SubElement(general, 'serial_number')
            serial_number_xml.text = computer.serial.decode('utf-8')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # ^ END: Create XML structure that will be sent through the api call
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>

        xml = ET.tostring(top)
        self._push_xml_handler(xml, computer.jss_id)

    def push_label_fields(self, computer_id, barcode_number, yellow_asset_tag, name_label):
        '''Pushes the following to the JSS:
                barcode number
                yellow asset tag number
            '''
        logger.info("push_label_fields(): activated")
        # logger.debug("  ARGS (" + computer_id + ", " + barcode_number + ", " + yellow_asset_tag + ", " + name_label + ")")
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # v BEGIN: Create XML structure that will be sent through the api call
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Top XML tag
        top = ET.Element('computer')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # General tag
        general = ET.SubElement(top, 'general')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # barcode_1 tag (white tag)
        if barcode_number != "":
            barcode_1_xml = ET.SubElement(general, 'barcode_1')
            barcode_1_xml.text = barcode_number.decode('utf-8')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # asset_tag tag (yellow tag)
        if yellow_asset_tag != "":
            yellow_asset_tag_xml = ET.SubElement(general, 'asset_tag')
            yellow_asset_tag_xml.text = yellow_asset_tag.decode('utf-8')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Extension attributes tag
        ext_attrs = ET.SubElement(top, 'extension_attributes')
        if name_label != "":
            # Extension attribute tag
            previous_computer_names__attr = ET.SubElement(ext_attrs, 'extension_attribute')

            # ID tag for previous computer name
            previous_computer_names_id = ET.SubElement(previous_computer_names__attr, 'id')
            previous_computer_names_id.text = '46'

            # Name tag for previous computer names
            previous_computer_names_name = ET.SubElement(previous_computer_names__attr, 'name')
            previous_computer_names_name.text = 'Previous Computer Names'

            # Value tag for budget source
            previous_computer_names_value = ET.SubElement(previous_computer_names__attr, 'value')
            previous_computer_names_value.text = name_label
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # ^ END: Create XML structure that will be sent through the api call
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        xml = ET.tostring(top)
        self._push_xml_handler(xml, computer_id)

    def push_xml_fields(self, xml, computer_id):
        tree = ET.parse(xml)
        xml = ET.tostring(tree.getroot(), encoding='utf-8')
        xml = re.sub("\n", "", xml)
        xml = re.sub("(>)\s+(<)", r"\1\2", xml)

        self._push_xml_handler(xml, computer_id)

    def push_offboard_fields(self, computer_id, offboard_fields):

        logger.debug("push_offboard_fields(): activated")

        # data entry: location
        building = offboard_fields['location']['building']
        department = offboard_fields['location']['department']
        email_address = offboard_fields['location']['email_address']
        phone = offboard_fields['location']['phone']
        phone_number = offboard_fields['location']['phone_number']
        position = offboard_fields['location']['position']
        real_name = offboard_fields['location']['real_name']
        realname = offboard_fields['location']['realname']
        room = offboard_fields['location']['room']
        username = offboard_fields['location']['username']

        # data entry: general
        name = offboard_fields['general']['computer_name']

        # data entry: remote management
        managed = offboard_fields['general']['remote_management']['managed']

        # data entry: extension attributes
        inventory_category = offboard_fields['extension_attributes']['Inventory Category']
        inventory_status = offboard_fields['extension_attributes']['Inventory Status']
        onboarding_ip = offboard_fields['extension_attributes']['Onboarding IP']

        # build XML object
        top = ET.Element('computer')

        # General xml fields
        general = ET.SubElement(top, 'general')

        computer_name_xml = ET.SubElement(general, 'name')
        computer_name_xml.text = name

        # general>remote management fields
        remote_management = ET.SubElement(general, 'remote_management')
        managed_xml = ET.SubElement(remote_management, 'managed')
        managed_xml.text = managed

        # Location xml fields
        location = ET.SubElement(top, 'location')

        username_xml = ET.SubElement(location, 'username')
        username_xml.text = username

        realname_xml = ET.SubElement(location, 'realname')
        realname_xml.text = realname

        real_name_xml = ET.SubElement(location, 'real_name')
        real_name_xml.text = real_name

        email_xml = ET.SubElement(location, 'email_address')
        email_xml.text = email_address

        position_xml = ET.SubElement(location, 'position')
        position_xml.text = position

        phone_xml = ET.SubElement(location, 'phone')
        phone_xml.text = phone

        phone_number_xml = ET.SubElement(location, 'phone_number')
        phone_number_xml.text = phone_number

        department_xml = ET.SubElement(location, 'department')
        department_xml.text = department

        building_xml = ET.SubElement(location, 'building')
        building_xml.text = building

        room_xml = ET.SubElement(location, 'room')
        room_xml.text = room

        # Extension attributes xml fields

        ext_attrs = ET.SubElement(top, 'extension_attributes')

        inventory_category_attr = ET.SubElement(ext_attrs, 'extension_attribute')

        inventory_category_id = ET.SubElement(inventory_category_attr, 'id')
        inventory_category_id.text = '19'

        inventory_category_name = ET.SubElement(inventory_category_attr, 'name')
        inventory_category_name.text = 'Inventory Category'

        inventory_category_value = ET.SubElement(inventory_category_attr, 'value')
        inventory_category_value.text = inventory_category

        inventory_status_attr = ET.SubElement(ext_attrs, 'extension_attribute')

        inventory_status_id = ET.SubElement(inventory_status_attr, 'id')
        inventory_status_id.text = '23'

        inventory_status_name = ET.SubElement(inventory_status_attr, 'name')
        inventory_status_name.text = 'Inventory Status'

        inventory_status_value = ET.SubElement(inventory_status_attr, 'value')
        inventory_status_value.text = inventory_status

        onboarding_ip_attr = ET.SubElement(ext_attrs, 'extension_attribute')

        onboarding_ip_id = ET.SubElement(onboarding_ip_attr, 'id')
        onboarding_ip_id.text = '24'

        onboarding_ip_name = ET.SubElement(onboarding_ip_attr, 'name')
        onboarding_ip_name.text = 'Onboarding IP'

        onboarding_ip_value = ET.SubElement(onboarding_ip_attr, 'value')
        onboarding_ip_value.text = onboarding_ip

        xml = ET.tostring(top)

        self._push_xml_handler(xml, computer_id)

        return True



    def set_offboard_fields(self, offboard_fields, inventory_status=None):

        logger.info("set_offboard_fields(): activated")

        if inventory_status == 'Salvage':

            new_prefix = '[SALV]-'.decode('utf-8')
            new_computer_name = new_prefix + offboard_fields['general']['serial_number']

        elif inventory_status == 'Storage':

            new_prefix = '[STOR]-'.decode('utf-8')
            new_computer_name = new_prefix + offboard_fields['general']['serial_number']

        else:

            raise SystemExit('Invalid inventory status. Please choose Salvage or Storage.')

        # offboard_fields['general'].pop('serial_number', None)

        offboard_fields['location'].update({'building': ''.decode('utf-8'),
                                            'department': ''.decode('utf-8'),
                                            'email_address': ''.decode('utf-8'),
                                            'phone': ''.decode('utf-8'),
                                            'phone_number': ''.decode('utf-8'),
                                            'position': ''.decode('utf-8'),
                                            'real_name': ''.decode('utf-8'),
                                            'realname': ''.decode('utf-8'),
                                            'room': ''.decode('utf-8'),
                                            'username': ''.decode('utf-8')})

        offboard_fields['general'].update({'computer_name': new_computer_name})

        offboard_fields['general']['remote_management'].update({'managed': 'False'.decode('utf-8')})

        offboard_fields['extension_attributes'].update({'Inventory Category': 'None'.decode('utf-8'),
                                                        'Inventory Status': inventory_status.decode('utf-8'),
                                                        'Onboarding IP': ''.decode('utf-8')})

        logger.debug("  offboard_fields: " + str(offboard_fields))
        logger.info("set_offboard_fields(): finished")

        return offboard_fields

    # REMOVE THIS FUNCTION
    def serial_equals_local_serial(self, computer_id):
        ''' Verifies whether or not the local serial number matches the JSS serial number. Returns True if they match,
        and false if they differ.
        '''
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        logger.info("is_jss_serial_correct" + ": activated")
        # Gets computer (local) serial number and serial number according to JSS
        local_serial = self.get_serial()
        tugboat_fields = self.get_tugboat_fields(computer_id)
        jss_serial = tugboat_fields['general']['serial_number']
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Checks if local serial and JSS serial are different. If they are, the JSS serial is stored for review.
        if local_serial != jss_serial:
            logger.debug('Serial numbers are different. Local serial number = ' + local_serial + " != " +
                         jss_serial + " = JSS serial number.")
            logger.info("is_jss_serial_correct" + ": succeeded")
            return False
        logger.info("is_jss_serial_correct" + ": succeeded")
        return True
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>

    def get_serial(self, computer_id):
        tugboat_fields = self.get_tugboat_fields(computer_id)
        jss_serial = tugboat_fields['general']['serial_number']
        return jss_serial

    def get_managed_status(self, jss_id):
        general_list_main = self.get_general_inventory(jss_id)
        remote_mangement_list = general_list_main['remote_management']
        return str(remote_mangement_list['managed'])

    def get_barcode(self, jss_id):
        barcode = self.get_tugboat_fields(jss_id)['general']['barcode_1']
        return barcode

    def get_asset(self, jss_id):
        asset = self.get_tugboat_fields(jss_id)['general']['asset_tag']
        return asset

    def get_name(self, jss_id):
        name = self.get_tugboat_fields(jss_id)['general']['computer_name']
        return name

    def enroll_computer(self):
        # ***REMOVED***/
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        logger.info("enroll" + ": activated")
        logger.info('Enrolling computer.')
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        jamf = '/usr/local/bin/jamf'
        cmd = [jamf, 'enroll', '-invitation', self.invite, '-noPolicy',
               '-noManage', '-verbose']
        # <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
        # Enroll computer
        try:
            enroll_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            logger.debug(enroll_output)
            logger.info('Enrolling finished.')
            return True
        # except subprocess.CalledProcessError as e:
        #     logger.error("  > " + str(e.output))
        #     logger.info(func_name() + ": failed")
        #     raise
        except (OSError, subprocess.CalledProcessError) as e:
            # if e.errno == 2:
            logger.error("Couldn't find " + jamf + ". Enrolling failed. " + str(e))
            try:
                jamf = '/Volumes/Storage/jamf'
                logger.info("Enrolling again. Now using " + jamf)

                conf_cmd = [jamf, 'createConf', '-url', self.jss_url, '-verifySSLCert', 'never']
                conf_output = subprocess.check_output(conf_cmd, stderr=subprocess.STDOUT)
                logger.debug(conf_output)
                enroll_cmd = [jamf, 'enroll', '-invitation', self.invite, '-noPolicy', '-noManage', '-verbose']
                enroll_output = subprocess.check_output(enroll_cmd, stderr=subprocess.STDOUT)
                logger.debug(enroll_output)
                logger.info('Enrolling finished.')
                return True
            except subprocess.CalledProcessError as e:
                logger.error(e.output)
                logger.info("enroll" + ": failed")
                raise
            except Exception as e:
                logger.error("  > Either the path to " + jamf + " is incorrect or JAMF has not "
                                                                "been installed on this computer. ")
                logger.error(e)
                logger.info("enroll" + ": failed")
                raise

    def _push_xml_handler(self, xml, computer_id):
        try:
            logger.debug("  Submitting XML: %r" % xml)

            opener = urllib2.build_opener(urllib2.HTTPHandler)
            computer_url = self.jss_url + '/JSSResource/computers/id/' + computer_id
            request = urllib2.Request(computer_url, data=xml)
            request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))
            request.add_header('Content-Type', 'text/xml')
            request.get_method = lambda: 'PUT'
            response = opener.open(request)

            logger.info("   HTML PUT response code: %i" % response.code)

        except urllib2.HTTPError as error:
            contents = error.read()
            print("HTTP error contents: %r" % contents)
            if error.code == 400:
                print("HTTP code %i: %s " % (error.code, "Request error."))
            elif error.code == 401:
                print("HTTP code %i: %s " % (error.code, "Authorization error."))
            elif error.code == 403:
                print("HTTP code %i: %s " % (error.code, "Permissions error."))
            elif error.code == 404:
                print("HTTP code %i: %s " % (error.code, "Resource not found."))
            elif error.code == 409:
                error_message = re.findall("Error: (.*)<", contents)
                print("HTTP code %i: %s %s" % (error.code, "Resource conflict.", error_message[0]))
            else:
                print("HTTP code %i: %s " % (error.code, "Misc HTTP error."))
            raise error
        except urllib2.URLError as error:
            print("URL error reason: %r" % error.reason)
            print("Error contacting JSS.")
            raise error
        except Exception as error:
            print("Error submitting to JSS. {}".format(error))
            raise error

    def _delete_handler(self, computer_id):
        try:
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            computer_url = self.jss_url + '/JSSResource/computers/id/' + computer_id
            request = urllib2.Request(computer_url)
            request.add_header('Authorization', 'Basic ' + base64.b64encode(self.username + ':' + self.password))
            request.get_method = lambda: 'DELETE'
            response = opener.open(request)

            logger.debug("  HTML DELETE response code: %i" % response.code)

        except urllib2.HTTPError as error:
            contents = error.read()
            print("HTTP error contents: %r" % contents)
            if error.code == 400:
                print("HTTP code %i: %s " % (error.code, "Request error."))
            elif error.code == 401:
                print("HTTP code %i: %s " % (error.code, "Authorization error."))
            elif error.code == 403:
                print("HTTP code %i: %s " % (error.code, "Permissions error."))
            elif error.code == 404:
                print("HTTP code %i: %s " % (error.code, "Resource not found."))
            elif error.code == 409:
                error_message = re.findall("Error: (.*)<", contents)
                print("HTTP code %i: %s %s" % (error.code, "Resource conflict.", error_message[0]))
            else:
                print("HTTP code %i: %s " % (error.code, "Misc HTTP error."))
            raise error
        except urllib2.URLError as error:
            print("URL error reason: %r" % error.reason)
            print("Error contacting JSS.")
            raise error
        except Exception as error:
            print("Error submitting to JSS. {}".format(error))
            raise error



cf = inspect.currentframe()
filename = inspect.getframeinfo(cf).filename
filename = os.path.basename(filename)
filename = os.path.splitext(filename)[0]
logger = loggers.FileLogger(name=filename, level=loggers.DEBUG)
logger.debug("Name of logger: " + filename)
