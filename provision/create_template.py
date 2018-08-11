from netmiko import ConnectHandler
from ncclient import manager
from jinja2 import Template
import yaml
import time

print("Reading in Device Device Details")
with open("command_sets.yml") as f:
    command_sets = yaml.load(f.read())

for device in command_sets["devices"]:
    print("Defining netmiko session details on DEVICE: {}".format(device["name"]))

    ch = ConnectHandler(device_type=device["device_type"],
                        ip=device["ip"],
                        username=device["username"],
                        password=device["password"],
                        port=device["ssh_port"])

        for command in