Blade-Runner
===========

Blade-Runner is a Python application that manages Mac computer systems through
API calls to a JAMF server. It has the ability to manage, off-board, update, and delete
JAMF records for a given computer, auto-generate documents populated
with data from the JAMF server, secure erase all internal disks, and notify Slack
channels of Blade-Runner's progress.

# Contents

* [Features](#features)
* [System Requirements](#system-requirements)
* [Configuration](#configuration)

# Features

### *JAMF Integration*
* Manage/unmanage computer.
* Off-board computer.
* Update computer record.
* Delete computer record.

### *Secure Erase*
* Secure erase all internal disks.

### *Auto-Generate Documents*
* Create a document populated with JAMF data for a given computer.

### *Auto-Print Documents*
* Print auto-generated documents to the default printer.

### *Slack Integration*
* Send Slack notifications on Blade-Runner's progress. Channel, URL, and
message are configurable.
* "Reminder of completion" daemon that sends Slack notifications on a given 
time interval after Blade-Runner has finished.

### *Plist/XML Configuration*
* JAMF config.
* Slack config.

# System Requirements

Blade-Runner requires Python 2.7.9 or higher, and is compatible on macOS 10.9 
(Mavericks) - 10.12 (Sierra). It has not been tested on OSes outside that 
range.

# Configuration
Blade-Runner is configured through plists and XML files. These configuration
files are used for JAMF, Slack, and Blade-Runner. The configuration files
are located in `blade-runner/private`. All of them must be configured before
running Blade-runner.

### JAMF Configuration
The JAMF configuration plist (`jss_server_config.plist`) contains the information
needed for Blade-Runner to run JAMF related tasks. The config contains the 
following keys:

* *username*
  * JAMF login username that will be used to make API calls to the JAMF server. 
* *password*
  * JAMF login password that will be used to make API calls to the JAMF server.
* *jss_url*
  * URL of the JAMF server to be queried.
* *invite*
  * Invitation code used to enroll a computer into the JAMF server. 
* *jamf_binary_1*
  * Location of `jamf` binary on computer. This is the primary `jamf` binary
  that will be used to enroll computers.
* *jamf_binary_2*
  * Secondary `jamf` binary location. Intended to be a location on an external
  hard drive, e.g., `/Volumes/my_external_drive/jamf` in the case that the 
  computer being enrolled doesn't have a `jamf` binary.

#### Example

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>username</key>
	<string>user1234</string>
	<key>password</key>
	<string>secret_pass123</string>
	<key>jss_url</key>
	<string>https://my.jamf.server.domain:portnumber</string>
	<key>invite</key>
	<string>1234567891234567891234567891234567890</string>
	<key>jamf_binary_1</key>
	<string>/usr/local/bin/jamf</string>
	<key>jamf_binary_2</key>
	<string>/Volumes/my_external_drive/jamf</string>
</dict>
</plist>
```

### Offboarding Configurations
Offboard configurations can have any name but must be `XML` files. These configs
contain the information to be sent to the JAMF server when offboarding. Upon 
starting Blade-Runner, an offboard configuration selection will be shown to the 
user. All XML files in `private` will be avialable for selection.

**The XML file must represent a valid string for JAMF's XML API calls.** The best
way to check this is to go to `https://my.jamf.server.domain:portnumber/api`,
click on `computers>computers/id>Try it out!`, and look at the available 
data in `XML Response Body`. Your configuration file's tags and structure should
only contain tags that exist in `XML Response Body`.

#### Examples

* Offboard configuration that only sets management status to false:
```
<computer>
  <general>
    <remote_management>
      <managed>false</managed>
    </remote_management>
  </general>
</computer>
```

* Offboard configuration that sets management status to false and clears all
  location fields:
```
<computer>
  <general>
    <remote_management>
      <managed>false</managed>
    </remote_management>
  </general>
  <location>
    <username></username>
    <realname></realname>
    <real_name></real_name>
    <email_address></email_address>
    <position></position>
    <phone></phone>
    <phone_number></phone_number>
    <department></department>
    <building></building>
    <room></room>
  </location>
</computer>
```

* Offboard configuration that sets management status to false and updates an
  extension attribute (extension attributes differ between JAMF servers):
```
<computer>
  <general>
    <name>[STOR]-</name>
    <remote_management>
      <managed>false</managed>
    </remote_management>
  </general>
  <extension_attributes>
    <extension_attribute>
      <id>12</id>
      <name>Inventory Status</name>
      <type>String</type>
      <value>Storage</value>
    </extension_attribute>
  </extension_attributes>
</computer>
```

### Search Parameters Configuration
The search parameters config (`search_params_config.plist`) determines the 
search parameters to be used in searching for a computer in JAMF. The 
Blade-Runner GUI will dynamically update according to these search parameters 
by only showing buttons that correspond to the enabled search parameters.

The available search parameters are `barcode 1`, `barcode 2`, `asset tag`, and 
`serial number`.

#### Example
* Config that updates Blade-Runner GUI to show `barcode 1`, `asset_tag`, and 
  `serial number` buttons and allows the user to search JAMF for a computer 
  using those search parameters:
```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>barcode_1</key>
	<string>True</string>
	<key>barcode_2</key>
	<string>False</string>
	<key>asset_tag</key>
	<string>True</string>
	<key>serial_number</key>
	<string>True</string>
</dict>
</plist>
```

### Verification Parameters Configuration







