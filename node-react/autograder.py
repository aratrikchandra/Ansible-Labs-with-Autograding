import json
import os
import subprocess
import requests
import configparser

def execute_command(command):
    """Execute a shell command and return the output and error."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            executable='/bin/bash'
        )
        return result.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return None, f"Error: {e.stderr.strip()}"

def parse_inventory():
    """Parse inventory.ini to get EC2 connection details"""
    config = configparser.ConfigParser(allow_no_value=True)
    config.read('inventory/inventory.ini')
    
    ec2_host = None
    user = 'ubuntu'
    key_path = 'inventory/ansible.pem'
    
    if 'webserver' in config:
        for host in config['webserver']:
            parts = host.split()
            if parts:
                ec2_host = parts[0]
                for param in parts[1:]:
                    if param.startswith('ansible_user='):
                        user = param.split('=')[1]
                    elif param.startswith('ansible_ssh_private_key_file='):
                        key_path = param.split('=')[1]
                break
    
    if not ec2_host:
        raise ValueError("EC2 host not found in inventory.ini")
    
    return ec2_host, user, key_path

def run_remote_command(command, key_path, user, host):
    """Execute a command on the EC2 instance via SSH"""
    ssh_cmd = f"ssh -i {key_path} -o StrictHostKeyChecking=no {user}@{host} '{command}'"
    return execute_command(ssh_cmd)

def verify_prerequisites(key_path, user, host):
    """Verify required packages are installed"""
    packages = ['curl', 'ca-certificates', 'gnupg']
    for pkg in packages:
        out, err = run_remote_command(f"dpkg -s {pkg}", key_path, user, host)
        if not out or 'Status: install ok installed' not in out:
            return False, f"{pkg} not installed"
    return True, "All prerequisites installed"

def verify_nodesource_repo(key_path, user, host):
    """Verify NodeSource repository exists"""
    # First check if the repository file exists
    out, err = run_remote_command(
        "[ -f /etc/apt/sources.list.d/nodesource.list ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "NodeSource repo file missing"
    return True, "NodeSource repo configured"

def verify_nodejs_installed(key_path, user, host):
    """Verify Node.js version 22.x"""
    out, err = run_remote_command("node --version", key_path, user, host)
    if out and out.startswith('v22.'):
        return True, f"Node.js {out} installed"
    return False, "Node.js 22.x not installed"

def verify_npm_version(key_path, user, host):
    """Verify npm version 10.9.2"""
    out, err = run_remote_command("npm --version", key_path, user, host)
    if out and out == '10.9.2':
        return True, f"npm {out} installed"
    return False, "npm 10.9.2 not installed"

def verify_app_directory(key_path, user, host):
    """Verify app directory permissions"""
    # First check if directory exists
    out, err = run_remote_command(
        "[ -d /home/ubuntu/app ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "App directory missing"

    # Check permissions with properly quoted format string
    out, err = run_remote_command(
        'stat -c "%U:%G %a" /home/ubuntu/app',  # Double quotes for format
        key_path, user, host
    )
    if out == 'ubuntu:ubuntu 755':
        return True, "App directory configured"
    return False, f"Invalid permissions: {out if out else 'Check failed'}"

def verify_app_files(key_path, user, host):
    """Verify application files copied"""
    out, err = run_remote_command(
        "[ -f /home/ubuntu/app/app.js ] && [ -f /home/ubuntu/app/package.json ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Application files present"
    return False, "Missing application files"

def verify_dependencies(key_path, user, host):
    """Verify npm dependencies installed"""
    out, err = run_remote_command(
        "test -d /home/ubuntu/app/node_modules && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Dependencies installed"
    return False, "node_modules missing"

def verify_app_running(host):
    """Verify application responds on port 5000"""
    try:
        response = requests.get(f"http://{host}:5000", timeout=5)
        if response.text.strip() == 'Node-Express App using Ansible':
            return True, "Application accessible"
        return False, "Unexpected response content"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def main():
    overall = {"data": []}
    data = []
    
    try:
        ec2_host, user, key_path = parse_inventory()
    except Exception as e:
        # If inventory parsing fails, fail all tests
        test_result = {
            "testid": "Inventory Configuration",
            "status": "failure",
            "score": 0,
            "maximum marks": 8,
            "message": f"Inventory error: {str(e)}"
        }
        overall["data"].append(test_result)
        with open('evaluate.json', 'w') as f:
            json.dump(overall, f, indent=4)
        return

    # Run Ansible playbook first
    playbook_cmd = f"ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory/inventory.ini playbook.yml"
    pb_out, pb_err = execute_command(playbook_cmd)
    
    test_cases = [
        {
            "testid": "Install prerequisites",
            "verify_function": verify_prerequisites,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Add NodeSource repository",
            "verify_function": verify_nodesource_repo,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Install Node.js",
            "verify_function": verify_nodejs_installed,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Install npm 10.9.2",
            "verify_function": verify_npm_version,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Create app directory",
            "verify_function": verify_app_directory,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Copy application files",
            "verify_function": verify_app_files,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Install dependencies",
            "verify_function": verify_dependencies,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Application running on port 5000",
            "verify_function": verify_app_running,
            "args": (ec2_host,),
            "maximum_marks": 1
        }
    ]

    for test in test_cases:
        test_result = {
            "testid": test["testid"],
            "status": "failure",
            "score": 0,
            "maximum marks": test["maximum_marks"],
            "message": ""
        }

        try:
            success, message = test["verify_function"](*test["args"])
            if success:
                test_result["status"] = "success"
                test_result["score"] = test["maximum_marks"]
            test_result["message"] = message
        except Exception as e:
            test_result["message"] = f"Verification error: {str(e)}"
        
        data.append(test_result)

    # Save results
    overall['data'] = data
    with open('evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    # Set strict permissions for the private key
    os.chmod('inventory/ansible.pem', 0o400)
    main()