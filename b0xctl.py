#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import os

# Add colorama for colored output
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    print("Installing colorama...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"])
    from colorama import init, Fore, Style
    init()

def load_config():
    # Use the real path of the script, not the symlink
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            if not config.get('instances'):
                print(f'{Fore.RED}Error: config.json must contain "instances" object.{Style.RESET_ALL}')
                sys.exit(1)
            return config
    except FileNotFoundError:
        print(f'{Fore.RED}Error: config.json not found at {config_path}{Style.RESET_ALL}')
        sys.exit(1)
    except json.JSONDecodeError:
        print(f'{Fore.RED}Error: config.json is not valid JSON.{Style.RESET_ALL}')
        sys.exit(1)

def get_instance_info(config, instance_name=None):
    if not instance_name:
        instance_name = config.get('default_instance')
        if not instance_name:
            print(f'{Fore.RED}Error: No instance specified and no default_instance in config.json{Style.RESET_ALL}')
            sys.exit(1)
    
    instance_info = config['instances'].get(instance_name)
    if not instance_info:
        print(f'{Fore.RED}Error: Instance "{instance_name}" not found in config.json{Style.RESET_ALL}')
        print(f'{Fore.YELLOW}Available instances: {", ".join(config["instances"].keys())}{Style.RESET_ALL}')
        sys.exit(1)
    
    return instance_name, instance_info['instance_id'], instance_info['region']

def run_aws_cli(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f'{Fore.RED}Command failed: {" ".join(args)}{Style.RESET_ALL}')
        print(f'{Fore.RED}{e.stderr.strip()}{Style.RESET_ALL}')
        sys.exit(1)

def get_instance_state(instance_id, region):
    try:
        output = run_aws_cli(['aws', 'ec2', 'describe-instances', '--instance-ids', instance_id, '--region', region, '--query', 'Reservations[0].Instances[0].State.Name', '--output', 'text'])
        return output.strip()
    except:
        return None

def print_instance_status(instance_name, instance_id, region):
    print(f'{Fore.CYAN}Checking status for instance {instance_name} ({instance_id})...{Style.RESET_ALL}')
    current_state = get_instance_state(instance_id, region)
    if current_state == 'stopped':
        print(f'\n{Fore.YELLOW}Instance {instance_name} is stopped.{Style.RESET_ALL}\n')
        return
    output = run_aws_cli(['aws', 'ec2', 'describe-instance-status', '--instance-ids', instance_id, '--region', region])
    try:
        data = json.loads(output)
        if data.get('InstanceStatuses'):
            status = data['InstanceStatuses'][0]
            state = status['InstanceState']['Name']
            instance_status = status['InstanceStatus']['Status']
            system_status = status['SystemStatus']['Status']
            az = status['AvailabilityZone']
            state_color = Fore.GREEN if state == 'running' else Fore.RED
            print(f"\n{Fore.CYAN}Instance Name: {instance_name}")
            print(f"{Fore.CYAN}Instance ID: {instance_id}")
            print(f"{Fore.CYAN}Availability Zone: {az}")
            print(f"{Fore.CYAN}State: {state_color}{state}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Instance Status: {Fore.GREEN if instance_status == 'ok' else Fore.RED}{instance_status}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}System Status: {Fore.GREEN if system_status == 'ok' else Fore.RED}{system_status}{Style.RESET_ALL}\n")
        else:
            print(f"{Fore.YELLOW}No status information available for instance {instance_name}{Style.RESET_ALL}")
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error parsing status output{Style.RESET_ALL}")
        print(output)

def main():
    parser = argparse.ArgumentParser(description='Control your EC2 instances.')
    parser.add_argument('command', choices=['start', 'stop', 'status', 'restart', 'list'], help='Action to perform')
    parser.add_argument('instance', nargs='?', help='Instance name or ID (optional, uses default if not specified)')
    args = parser.parse_args()

    config = load_config()

    if args.command == 'list':
        print(f'\n{Fore.CYAN}Available instances:{Style.RESET_ALL}')
        for name, info in config['instances'].items():
            state = get_instance_state(info['instance_id'], info['region'])
            state_color = Fore.GREEN if state == 'running' else Fore.RED if state == 'stopped' else Fore.YELLOW
            print(f"{Fore.CYAN}{name}: {state_color}{state or 'unknown'}{Style.RESET_ALL} ({info['instance_id']})")
        print()
        return

    instance_name, instance_id, region = get_instance_info(config, args.instance)

    if args.command == 'start':
        current_state = get_instance_state(instance_id, region)
        if current_state == 'running':
            print(f'{Fore.YELLOW}Instance {instance_name} is already running.{Style.RESET_ALL}')
            return
        print(f'{Fore.CYAN}Starting instance {instance_name}...{Style.RESET_ALL}')
        run_aws_cli(['aws', 'ec2', 'start-instances', '--instance-ids', instance_id, '--region', region])
        print(f'{Fore.GREEN}Instance {instance_name} started successfully.{Style.RESET_ALL}')
    elif args.command == 'stop':
        current_state = get_instance_state(instance_id, region)
        if current_state == 'stopped':
            print(f'{Fore.YELLOW}Instance {instance_name} is already stopped.{Style.RESET_ALL}')
            return
        print(f'{Fore.CYAN}Stopping instance {instance_name}...{Style.RESET_ALL}')
        run_aws_cli(['aws', 'ec2', 'stop-instances', '--instance-ids', instance_id, '--region', region])
        print(f'{Fore.GREEN}Instance {instance_name} stopped successfully.{Style.RESET_ALL}')
    elif args.command == 'status':
        print_instance_status(instance_name, instance_id, region)
    elif args.command == 'restart':
        print(f'{Fore.CYAN}Restarting instance {instance_name}...{Style.RESET_ALL}')
        run_aws_cli(['aws', 'ec2', 'reboot-instances', '--instance-ids', instance_id, '--region', region])
        print(f'{Fore.GREEN}Instance {instance_name} restarted successfully.{Style.RESET_ALL}')

if __name__ == '__main__':
    main() 