import json
import os
import subprocess
import configparser
import time

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
    
    if 'DB-server' in config:
        for host in config['DB-server']:
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

def verify_keyrings_directory(key_path, user, host):
    """Verify /usr/share/keyrings directory configuration"""
    # Check directory exists with correct permissions
    out, err = run_remote_command(
        'stat -c "%F %U:%G %a" /usr/share/keyrings', key_path, user, host
    )
    
    if not out:
        return False, "Keyrings directory missing"
    
    parts = out.split()
    if (parts[0] != 'directory' or 
        parts[1] != 'root:root' or 
        parts[2] != '755'):
        return False, f"Invalid directory configuration: {out}"
    
    return True, "Keyrings directory configured properly"

def verify_mongod_config(key_path, user, host):
    """Verify MongoDB configuration file matches template"""
    # First check if config file exists
    out, err = run_remote_command(
        "[ -f /etc/mongod.conf ] && echo exists", key_path, user, host
    )
    if out != "exists":
        return False, "Mongod config file missing"
    
    # Get local template content
    try:
        with open('roles/database/templates/mongod.conf.j2', 'r') as f:
            local_content = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        return False, f"Local template error: {str(e)}"
    
    # Get remote config content
    remote_content, err = run_remote_command(
        "cat /etc/mongod.conf", key_path, user, host
    )
    if not remote_content:
        return False, "Failed to read remote config"
    
    remote_lines = [line.strip() for line in remote_content.split('\n') if line.strip()]
    
    # Compare content line-by-line (ignoring whitespace)
    if len(local_content) != len(remote_lines):
        return False, "Config content length mismatch"
    
    for local_line, remote_line in zip(local_content, remote_lines):
        if local_line != remote_line:
            return False, f"Config mismatch:\nExpected: {local_line}\nFound: {remote_line}"
    
    # Check file permissions
    out, err = run_remote_command(
        'stat -c "%U:%G %a" /etc/mongod.conf', key_path, user, host
    )
    if out != "mongodb:mongodb 644":
        return False, f"Invalid file permissions: {out}"
    
    return True, "MongoDB configuration matches template with correct permissions"

def verify_prerequisites(key_path, user, host):
    """Verify required packages are installed"""
    packages = ['curl', 'gnupg']
    for pkg in packages:
        out, err = run_remote_command(f"dpkg -s {pkg}", key_path, user, host)
        if not out or 'Status: install ok installed' not in out:
            return False, f"{pkg} not installed"
    return True, "All prerequisites installed"

def verify_mongodb_repo(key_path, user, host):
    """Verify MongoDB repository exists"""
    out, err = run_remote_command(
        "[ -f /etc/apt/sources.list.d/mongodb-org-8.0.list.list ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "MongoDB repo file missing"
    return True, "MongoDB repo configured"

def verify_gpg_key(key_path, user, host):
    """Verify MongoDB GPG key exists"""
    out, err = run_remote_command(
        "[ -f /usr/share/keyrings/mongodb-server-8.0.gpg ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "MongoDB GPG key missing"
    return True, "MongoDB GPG key present"

def verify_mongodb_versions(key_path, user, host):
    """Verify MongoDB packages installed with exact versions"""
    packages = {
        'mongodb-org': '8.0.5',
        'mongodb-org-database': '8.0.5',
        'mongodb-org-server': '8.0.5',
        'mongodb-org-shell': '8.0.5',
        'mongodb-org-tools': '8.0.5',
        'mongodb-mongosh': '2.4.2'
    }
    
    for pkg, version in packages.items():
        out, err = run_remote_command(f"apt-cache policy {pkg} | grep 'Installed'", key_path, user, host)
        if not out or version not in out:
            return False, f"{pkg} version mismatch"
    return True, "All MongoDB packages installed correctly"

def verify_directories(key_path, user, host):
    """Verify MongoDB directories exist with proper permissions"""
    dirs = ['/var/lib/mongodb', '/var/log/mongodb']
    for d in dirs:
        out, err = run_remote_command(
            f'stat -c "%U:%G %a" {d}', key_path, user, host
        )
        if out != 'mongodb:mongodb 755':
            return False, f"Invalid permissions for {d}"
    return True, "MongoDB directories configured properly"

def verify_service_status(key_path, user, host):
    """Verify MongoDB service is enabled and running"""
    out_active, err = run_remote_command(
        "systemctl is-active mongod", key_path, user, host
    )
    out_enabled, err = run_remote_command(
        "systemctl is-enabled mongod", key_path, user, host
    )
    if out_active == 'active' and out_enabled == 'enabled':
        return True, "Service running and enabled"
    return False, f"Service state: active={out_active}, enabled={out_enabled}"

def main():
    overall = {"data": []}
    data = []
    
    try:
        ec2_host, user, key_path = parse_inventory()
    except Exception as e:
        test_result = {
            "testid": "Inventory Configuration",
            "status": "failure",
            "score": 0,
            "maximum marks": 1,
            "message": f"Inventory error: {str(e)}"
        }
        overall["data"].append(test_result)
        with open('../evaluate.json', 'w') as f:
            json.dump(overall, f, indent=4)
        return

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
            "testid": "Keyrings directory setup",
            "verify_function": verify_keyrings_directory,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Add MongoDB repository",
            "verify_function": verify_mongodb_repo,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Import GPG key",
            "verify_function": verify_gpg_key,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Install MongoDB packages",
            "verify_function": verify_mongodb_versions,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Create MongoDB directories",
            "verify_function": verify_directories,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Configure MongoDB",
            "verify_function": verify_mongod_config,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Service status",
            "verify_function": verify_service_status,
            "args": (key_path, user, ec2_host),
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

    overall['data'] = data
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    os.chmod('inventory/ansible.pem', 0o600)
    main()