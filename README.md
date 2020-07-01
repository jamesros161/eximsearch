# Exim Search Utility

This is a fully interactive console UI application build on Urwid. The purpose of this program is to simplify the parsing, searching and interperating of the exim_mainlogs. The primary features include the ability to search the multiple log files simultaneously ( including gzipped logs), multi-threaded search processes, easy cross reference searches of various entry fields, search filters ( sender, recipient, date, and message type), and cPanel user sending stats.

### Prerequisites

This application was developed using Python2.7. The following modules are imported in the application, but are included in the Python Standard Library:

datetime
os
subprocess
sys
json
re
shlex
gzip
time
datetime
logging
collections
socket
threading
getpass
multiprocessing

In addition to the modules included in the Python Standard Library, you will need the urwid moduels, however they have been bundled with this application, so you should not actually need to install urwid. If you do however, it can be found (http://urwid.org)
  
This will have to be run on a server with cPanel / WHM 11+ . This must be run as root or sudo. 

*** Please note, that due to the typical file permissions of the /var/log/exim_mainlog, this application will need to be run as either root, or run as sudo.

## Built With

[UAPI](https://documentation.cpanel.net/display/DD/Guide+to+UAPI) - The API used to interface with cPanel

[Urwid](http://urwid.org/) - Urwid is the library used to create the UI

## Authors

* **James Rosado** - *Initial work* - [twmsllc](https://github.com/twmsllc)

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE - see the LICENSE file for details

