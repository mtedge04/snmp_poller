Edit the snmp_config.txt and enter the subnet, community - keep version at v2c
Run the poller - sudo python3 snmp_poller_2.py
This creates a usable device.yml file in the directory you run this. It can be copied to /etc/elastiflow/snmp/devices/
