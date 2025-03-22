import subprocess
import re
import os

# Get IP Addresses (Ethernet and/or WiFi)
def get_ip_addresses():
    interfaces = ['eth0', 'wlan0']
    ip_info = {}
    for interface in interfaces:
        try:
            result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            ip = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
            ip_info[interface] = ip.group(1) if ip else 'Not Connected'
        except Exception as e:
            ip_info[interface] = f'Error: {str(e)}'
    return ip_info

# Get List of WiFi Networks
def list_wifi_networks():
    networks = []
    result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], capture_output=True, text=True)
    ssids = re.findall(r'ESSID:"(.*?)"', result.stdout)
    networks = list(set(ssids))  # remove duplicates
    return networks

# Set WiFi Credentials
def set_wifi_credentials(ssid, password):
    wpa_config = f'''
network={{
    ssid="{ssid}"
    psk="{password}"
}}
'''
    try:
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a') as file:
            file.write(wpa_config)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'])
        return True
    except Exception as e:
        return f'Error: {str(e)}'
def set_ip_mode(interface, mode, static_ip=None, gateway=None, dns='8.8.8.8 8.8.4.4'):
    dhcpcd_conf = '/etc/dhcpcd.conf'

    if mode == 'static' and static_ip:
        if not gateway:
            # Assume gateway is first IP (.1) of the subnet
            gateway = '.'.join(static_ip.split('.')[:3] + ['1'])

    try:
        with open(dhcpcd_conf, 'r') as file:
            lines = file.readlines()

        # Remove old static config for interface
        start_idx = None
        for idx, line in enumerate(lines):
            if line.strip() == f'interface {interface}':
                start_idx = idx
                break

        if start_idx is not None:
            end_idx = start_idx
            while end_idx < len(lines) and lines[end_idx].strip():
                end_idx += 1
            del lines[start_idx:end_idx]

        if mode == 'static' and static_ip:
            static_config = f'''
interface {interface}
static ip_address={static_ip}/24
static routers={gateway}
static domain_name_servers={dns}
'''
            lines.append(static_config)

        with open(dhcpcd_conf, 'w') as file:
            file.writelines(lines)

        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'])
        return True

    except Exception as e:
        return f'Error: {str(e)}'


# Example Usage:
if __name__ == "__main__":
    # 1. Get IP Addresses
    ips = get_ip_addresses()
    print("IP Addresses:", ips)

    # 2. List available WiFi networks
    networks = list_wifi_networks()
    print("Available WiFi Networks:", networks)

    # 3. Set WiFi credentials (Example)
    # set_wifi_credentials('YourSSID', 'YourPassword')

    # 4. Set DHCP or Static IP (Example)
    # DHCP Example:
    # set_ip_mode('eth0', 'dhcp')

    # Static IP Example:
    # set_ip_mode('eth0', 'static', '192.168.1.100', '192.168.1.1', '8.8.8.8')
