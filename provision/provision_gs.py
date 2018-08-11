from netmiko import ConnectHandler
from ncclient import manager
from jinja2 import Template
import yaml
import time

# I'd prefer to replace this with commands coming from the yaml file
initial_config = [
    'netconf',
    'netconf-yang',
    'restconf',
    'ip http server',
    'ip http secure-server',
    'iox'
]

# I'd prefer to replace this with commands coming from the yaml file
nat_config = [
    'interface VirtualPortGroup0',
    'ip nat inside',
]

# I'd prefer to replace this with commands coming from the yaml file
guestshell_config = [
    'app-hosting appid guestshell',
    'vnic gateway1 virtualportgroup 0 guest-interface 0 guest-ipaddress 192.168.35.2 netmask 255.255.255.0 gateway 192.168.35.1 name-server 8.8.8.8 default',
    'resource profile custom cpu 1500 memory 512',
]

# I'd prefer to replace this with commands coming from the yaml file
guestshell_enable = ('guestshell enable')

#Reading in the entire YAML file for use in various templates
print("Reading in Device Device Details")
with open("device_details.yml") as f:
    device_details = yaml.load(f.read())

# Create the NETCONF template for creating interfaces
print("Setting Up NETCONF Templates")
with open("templates/netconf_interface_template.j2") as f:
    interface_template = Template(f.read())

# Create the NETCONF template for configuring NAT
# The template will not allow for configuring NAT inside on the VirtualPortGroup - Pushed via Netmiko
with open("templates/netconf_nat_template.j2") as f:
    nat_template = Template(f.read())

# Creating various .xml configuraitons
print("Creating Device Configurations")
for device in device_details["devices"]:
    print("Device: {}".format(device["name"]))

    #Creates interface ,xml configuration
    print("Creating Interface Configurations from Templates")
    with open("netconf_configs/{}_layer3.cfg".format(device["name"]), "w") as f:
        int_config = interface_template.render(interfaces=device["interfaces"])
        f.write(int_config)

    #Creates NAT .xml configuration
    print("Creating NAT Configurations from Templates")
    with open("netconf_configs/{}_nat.cfg".format(device["name"]), "w") as f:
        nat_config = nat_template.render(nat=device["nat"])
        f.write(nat_config)

# Creating session details to be used by Netmiko. The intention is to reuse 'ch' for calling Netmiko sessions.
for device in device_details["devices"]:
    print("Defining netmiko session details on DEVICE: {}".format(device["name"]))
    ch = ConnectHandler(device_type=device["device_type"],
                        ip=device["ip"],
                        username=device["username"],
                        password=device["password"],
                        port=device["ssh_port"])

# I'd prefer this not to happen here. When I run the script the following section (used to define the NETCONF session)
# it fails as NETCONF is not running on the remote device.
print("Sending Initial Configuration with Netmiko")
initial_resp = ch.send_config_set(initial_config)

# Just pausing the script waiting for NETCONF to start
print("Pausing 45 seconds for NETCONF to Start on Router")
time.sleep(45)

# Defining the session details used by NETCONF. Calling it as 'm' in the various commands.
for device in device_details["devices"]:
    print("Defining netconf session details on DEVICE: {}".format(device["name"]))

    m = manager.connect(host=device["ip"],
                         username=device["username"],
                         password=device["password"],
                         port=device["netconf_port"],
                         allow_agent=False,
                         look_for_keys=False,
                         hostkey_verify=False)

# Sending interface configurations to the router via NETCONF
print("Sending Interface Configuration with Ncclient")
interface_resp = m.edit_config(int_config, target = 'running')

# Without this sleep timer the remote device kicks back a an RPC error
print("Pausing 5 seconds for Ncclient")
time.sleep(5)

# Sending NAT configurations to the router via NETCONF
print("Sending NAT Configuration with Ncclient")
nat_resp = m.edit_config(nat_config, target = 'running')

# Sending CLI command to configure 'ip nat inside' on VirtualPortGroup due to lack of YANG model support
print("Sending Additional NAT Config with Netmiko")
nat_vpg_resp = ch.send_config_set((nat_config))

# Configuring Guestshell via CLI
print("Sending Guestshell Config Netmiko")
guestshell_resp = ch.send_config_set((guestshell_config))

# Enabling Guestshell
print("Enabling Guestshell Netmiko")
enable_gs_resp = ch.send_command((guestshell_enable))

# Temp. command just to verify that GuestShell is running at the end.
print("Test Guestshell Status")
pwd = ch.send_command('guestshell run pwd')
print(pwd)