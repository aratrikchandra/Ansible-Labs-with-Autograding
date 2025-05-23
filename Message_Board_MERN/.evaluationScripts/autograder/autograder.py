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
    
    if 'appserver' in config:
        for host in config['appserver']:
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
    packages = ['curl', 'ca-certificates', 'gnupg', 'nginx']
    for pkg in packages:
        out, err = run_remote_command(f"dpkg -s {pkg}", key_path, user, host)
        if not out or 'Status: install ok installed' not in out:
            return False, f"{pkg} not installed"
    return True, "All prerequisites installed"

# MongoDB Verification Functions
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

def verify_mongodb_service(key_path, user, host):
    out_active, _ = run_remote_command("systemctl is-active mongod", key_path, user, host)
    out_enabled, _ = run_remote_command("systemctl is-enabled mongod", key_path, user, host)
    if out_active == 'active' and out_enabled == 'enabled':
        return True, "MongoDB service running"
    return False, f"Service state: active={out_active}, enabled={out_enabled}"

# Node/React Verification Functions
def verify_nodesource_repo(key_path, user, host):
    """Verify NodeSource repository exists"""
    out, err = run_remote_command(
        "[ -f /etc/apt/sources.list.d/nodesource.list ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "NodeSource repo file missing"
    return True, "NodeSource repo configured"
def verify_nodejs_installed(key_path, user, host):
    out, err = run_remote_command("node --version", key_path, user, host)
    if out and out.startswith('v22.'):
        return True, f"Node.js {out} installed"
    return False, "Node.js 22.x missing"
def verify_npm_version(key_path, user, host):
    """Verify npm version 10.9.2"""
    out, err = run_remote_command("npm --version", key_path, user, host)
    if out and out == '10.9.2':
        return True, f"npm {out} installed"
    return False, "npm 10.9.2 not installed"
def verify_app_directory(key_path, user, host):
    """Verify Node.js app directory permissions"""
    out, err = run_remote_command(
        "[ -d /home/ubuntu/app ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "Node.js app directory missing"
    out, err = run_remote_command(
        'stat -c "%U:%G %a" /home/ubuntu/app',
        key_path, user, host
    )
    if out == 'ubuntu:ubuntu 755':
        return True, "Node.js app directory configured"
    return False, f"Invalid permissions: {out}"
def verify_app_files(key_path, user, host):
    """Verify Node.js application files copied"""
    out, err = run_remote_command(
        "[ -f /home/ubuntu/app/app.js ] && [ -f /home/ubuntu/app/package.json ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Node.js files present"
    return False, "Missing Node.js files"

def verify_dependencies(key_path, user, host):
    """Verify Node.js dependencies installed"""
    out, err = run_remote_command(
        "test -d /home/ubuntu/app/node_modules && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Node.js dependencies installed"
    return False, "Node.js node_modules missing"

def verify_systemd_service(key_path, user, host):
    """Verify systemd service file exists"""
    out, err = run_remote_command(
        "[ -f /etc/systemd/system/node_app.service ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Systemd service created"
    return False, "Systemd service missing"

# Front-End Verification
def verify_react_app_directory(key_path, user, host):
    """Verify React app directory exists"""
    out, err = run_remote_command(
        "[ -d /home/ubuntu/react-app ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "React app directory missing"
    out, err = run_remote_command(
        'stat -c "%U:%G %a" /home/ubuntu/react-app',
        key_path, user, host
    )
    if out == 'ubuntu:ubuntu 755':
        return True, "React app directory configured"
    return False, f"Invalid permissions: {out}"

def verify_react_files_copied(key_path, user, host):
    """Verify React files copied"""
    out, err = run_remote_command(
        "[ -f /home/ubuntu/react-app/package.json ] && [ -d /home/ubuntu/react-app/src ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "React files present"
    return False, "Missing React files"

def verify_react_dependencies(key_path, user, host):
    """Verify React dependencies installed"""
    out, err = run_remote_command(
        "test -d /home/ubuntu/react-app/node_modules && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "React dependencies installed"
    return False, "React node_modules missing"

def verify_react_build_directory(key_path, user, host):
    """Verify React build directory exists"""
    out, err = run_remote_command(
        "[ -d /home/ubuntu/react-app/build ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "React build directory exists"
    return False, "React build directory missing"

def verify_react_static_directory(key_path, user, host):
    """Verify static files directory"""
    out, err = run_remote_command(
        "[ -d /var/www/react-app ] && echo exists",
        key_path, user, host
    )
    if out != "exists":
        return False, "Static directory missing"
    out, err = run_remote_command(
        'stat -c "%U:%G %a" /var/www/react-app',
        key_path, user, host
    )
    if out == 'ubuntu:ubuntu 755':
        return True, "Static directory configured"
    return False, f"Invalid permissions: {out}"

def verify_react_build_deployed(key_path, user, host):
    """Verify React build deployed"""
    out, err = run_remote_command(
        "[ -f /var/www/react-app/index.html ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "React build deployed"
    return False, "React build files missing"

# ngnix config
def verify_nginx_config(key_path, user, host):
    """Verify Nginx configuration"""
    out, err = run_remote_command(
        "[ -f /etc/nginx/sites-available/react_node.conf ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Nginx config present"
    return False, "Nginx config missing"

def verify_nginx_site_enabled(key_path, user, host):
    """Verify Nginx site enabled"""
    out, err = run_remote_command(
        "[ -L /etc/nginx/sites-enabled/react_node.conf ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Nginx site enabled"
    return False, "Nginx site not enabled"

def verify_nginx_default_site_removed(key_path, user, host):
    """Verify default Nginx site removed"""
    out, err = run_remote_command(
        "[ ! -f /etc/nginx/sites-enabled/default ] && echo exists",
        key_path, user, host
    )
    if out == 'exists':
        return True, "Default site removed"
    return False, "Default site present"

def verify_nginx_running(key_path, user, host):
    """Verify Nginx service status"""
    out, err = run_remote_command("systemctl is-active nginx", key_path, user, host)
    if out == 'active':
        return True, "Nginx running"
    return False, f"Nginx not running: {out}"

def verify_api_access(host):
    try:
        response = requests.get(f"http://{host}/api/messages", timeout=5)
        if response.status_code == 200:
            return True, "API accessible"
        return False, f"API status: {response.status_code}"
    except Exception as e:
        return False, f"API connection failed: {str(e)}"

def verify_frontend_access(host):
    try:
        response = requests.get(f"http://{host}", timeout=5)
        if response.status_code == 200 and '<div id="root"></div>' in response.text:
            return True, "Frontend accessible"
        return False, "Frontend content missing"
    except Exception as e:
        return False, f"Frontend connection failed: {str(e)}"

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

    # Run Ansible playbook
    playbook_cmd = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory/inventory.ini playbook.yml"
    execute_command(playbook_cmd)

    test_cases = [
        {
            "testid": "Install prerequisites",
            "func": verify_prerequisites,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        # MongoDB Tests
        {"testid": "MongoDB Keyrings Directory", "func": verify_keyrings_directory, "args": (key_path, user, ec2_host), "marks": 1},
        {
            "testid": "Import GPG key",
            "func": verify_gpg_key,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Add MongoDB repository",
            "func": verify_mongodb_repo,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {"testid": "MongoDB Packages", "func": verify_mongodb_versions, "args": (key_path, user, ec2_host), "marks": 1},
        {
            "testid": "Create MongoDB directories",
            "func": verify_directories,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {"testid": "MongoDB Configuration", "func": verify_mongod_config, "args": (key_path, user, ec2_host), "marks": 1},
        {"testid": "MongoDB Service", "func": verify_mongodb_service, "args": (key_path, user, ec2_host), "marks": 1},
        
        # Node.js Tests
        {
            "testid": "Add NodeSource repository",
            "func": verify_nodesource_repo,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {"testid": "Node.js Installation", "func": verify_nodejs_installed, "args": (key_path, user, ec2_host), "marks": 1},
        {
            "testid": "Install npm 10.9.2",
            "func": verify_npm_version,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {"testid": "App Directory", "func": verify_app_directory, "args": (key_path, user, ec2_host), "marks": 1},
        {
            "testid": "Copy Node.js files",
            "func": verify_app_files,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Install Node.js dependencies",
            "func": verify_dependencies,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Create systemd service",
            "func": verify_systemd_service,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        
        # React/Nginx Tests
        {
            "testid": "Create React app directory",
            "func": verify_react_app_directory,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Copy React files",
            "func": verify_react_files_copied,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Install React dependencies",
            "func": verify_react_dependencies,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Build React application",
            "func": verify_react_build_directory,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Create static directory",
            "func": verify_react_static_directory,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Deploy React build",
            "func": verify_react_build_deployed,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Configure Nginx",
            "func": verify_nginx_config,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Enable Nginx site",
            "func": verify_nginx_site_enabled,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Remove default site",
            "func": verify_nginx_default_site_removed,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {
            "testid": "Nginx service status",
            "func": verify_nginx_running,
            "args": (key_path, user, ec2_host),
            "marks": 1
        },
        {"testid": "API Access", "func": verify_api_access, "args": (ec2_host,), "marks": 1},
        {"testid": "Frontend Access", "func": verify_frontend_access, "args": (ec2_host,), "marks": 1}
    ]

    for test in test_cases:
        test_result = {
            "testid": test["testid"],
            "status": "failure",
            "score": 0,
            "maximum marks": test["marks"],
            "message": ""
        }

        try:
            # Handle end-to-end test
            success, msg = test["func"](*test["args"])
            if success:
                test_result["status"] = "success"
                test_result["score"] = test["marks"]
            test_result["message"] = msg
        except Exception as e:
            test_result["message"] = f"Verification error: {str(e)}"
        
        data.append(test_result)

    overall['data'] = data
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    os.chmod('inventory/ansible.pem', 0o600)
    main()