import subprocess
import ipaddress
import yaml

def read_config(filename="snmp_config.txt"):
    # Read configuration from file
    config = {}
    with open(filename, "r") as file:
        for line in file:
            key, value = map(str.strip, line.split(":"))
            config[key.lower()] = value
    return config

def poll_device(ip, communities, version, v3_config=None):
    for community in communities:
        if version == 3 and v3_config:
            # SNMP OID for system description
            oid_system_description = "iso.3.6.1.2.1.1.1.0"

            # Construct the SNMP command for SNMPv3
            snmp_cmd = [
                "snmpwalk",
                "-v3",
                "-l", f"authPriv",
                "-u", v3_config["username"],
                "-a", v3_config["authentication_protocol"],
                "-A", v3_config["authentication_passphrase"],
                "-x", v3_config["privacy_protocol"],
                "-X", v3_config["privacy_passphrase"],
                ip,
                oid_system_description
            ]
        else:
            # SNMP OID for system description
            oid_system_description = "iso.3.6.1.2.1.1.1.0"

            # Construct the SNMP command for SNMPv1/v2c
            snmp_cmd = [
                "snmpwalk",
                f"-v{version}",
                "-c", community,
                ip,
                oid_system_description
            ]

        try:
            # Run the SNMP command
            result = subprocess.check_output(snmp_cmd, stderr=subprocess.STDOUT, text=True)
            print(f"SNMP Output for {ip} with community {community}:\n{result}")
            return result.strip(), ip, community, version
        except subprocess.CalledProcessError as e:
            # Print an error message for the device
            print(f"Error for {ip} with community {community}: {e.output.strip()}")

    # Return None if none of the communities were successful
    return None, ip, communities, version

def get_device_group(system_description):
    # Map system descriptions to device groups
    mappings = {
        "vyos": "vyos",
        "cisco": "cisco_c1000",
        "juniper": "juniper_mx",
        "arista": "arista",
        "ubiquiti": "ubiquiti_edgemax",
        "linux": "linux",
        "macos": "macos",
        "calix": "calix_axos",
    }

    # Check if any substring in mappings is present in the system_description
    for substring, group in mappings.items():
        if substring.lower() in system_description.lower():
            return group

    return "generic"

def write_to_yaml(device_data, communities):
    # Write the device data to the YAML file with a divider
    with open("device.yml", "a") as output_file:
        # Include the IP as the first entry
        ip = device_data.pop("ip")
        yaml_entry = {ip: device_data}
        # Include 'ip:' as another entry
        yaml_entry[ip]["ip"] = ip
        # Include the communities in the device data
        yaml_entry[ip]["communities"] = communities
        #yaml.dump(yaml_entry, output_file, default_flow_style=False, explicit_start=True)
        yaml.dump(yaml_entry, output_file, default_flow_style=False)
        output_file.write("\n")

def main():
    # Read configuration from file
    config = read_config()

    # Retrieve configuration values
    subnet = config.get("subnet", "192.168.1.0/24")
    communities_str = config.get("community", "public")
    communities = [c.strip() for c in communities_str.split(",")]

    # Allow SNMP version to be provided as a string in the config file
    snmp_version_str = config.get("snmp_version", "2")
    
    if snmp_version_str.lower() == "2c":
        snmp_version = "2c"
        v3_config = None
    elif snmp_version_str.lower() == "3":
        snmp_version = 3
        v3_config = {
            "username": config.get("username", ""),
            "authentication_protocol": config.get("authentication_protocol", ""),
            "authentication_passphrase": config.get("authentication_passphrase", ""),
            "privacy_protocol": config.get("privacy_protocol", ""),
            "privacy_passphrase": config.get("privacy_passphrase", ""),
        }
    else:
        print("Unsupported SNMP version in configuration.")
        return

    # Iterate over devices in the subnet
    for ip in ipaddress.IPv4Network(subnet, strict=False).hosts():
        ip = str(ip)
        result, _, _, _ = poll_device(ip, communities, snmp_version, v3_config)
        # Only include devices that responded successfully
        if result is not None:
            # Determine the device group based on the system description
            system_description = result.lower()
            device_group = get_device_group(system_description)

            # Define the device data
            device_data = {
                "ip": ip,
                "port": 161,
                "poll_interval": 120,
                "timeout": 3000,
                "retries": 2,
                "exponential_timeout": False,
                "version": snmp_version,
                "device_groups": [device_group],
            }

            # Include v3_credentials if it is a version 3 entry
            if snmp_version == 3:
                device_data["v3_credentials"] = v3_config

            # Write the device data to the YAML file
            write_to_yaml(device_data, communities)

if __name__ == "__main__":
    main()
