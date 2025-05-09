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
    packages = ['curl', 'ca-certificates', 'gnupg', 'nginx']
    for pkg in packages:
        out, err = run_remote_command(f"dpkg -s {pkg}", key_path, user, host)
        if not out or 'Status: install ok installed' not in out:
            return False, f"{pkg} not installed"
    return True, "All prerequisites installed"

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

def verify_service_running(key_path, user, host):
    """Verify Node.js service is active"""
    out_active, err = run_remote_command(
        "systemctl is-active node_app",
        key_path, user, host
    )
    out_enabled, err = run_remote_command(
        "systemctl is-enabled node_app",
        key_path, user, host
    )
    if out_active == 'active' and out_enabled == 'enabled':
        return True, "Service running and enabled"
    return False, f"Service state: active={out_active}, enabled={out_enabled}"

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

def verify_api_proxy(host):
    """Verify API accessible via Nginx proxy"""
    try:
        response = requests.get(f"http://{host}/api", timeout=5)
        if response.text.strip() == 'Node-Express App using Ansible':
            return True, "API accessible via Nginx"
        return False, "Unexpected API response"
    except Exception as e:
        return False, f"API connection failed: {str(e)}"

def verify_react_frontend(host):
    """Verify React frontend accessible"""
    try:
        response = requests.get(f"http://{host}", timeout=5)
        if '<div id="root"></div>' in response.text:
            return True, "React frontend served"
        return False, "React content not found"
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
        with open('evaluate.json', 'w') as f:
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
            "testid": "Create Node.js app directory",
            "verify_function": verify_app_directory,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Copy Node.js files",
            "verify_function": verify_app_files,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Install Node.js dependencies",
            "verify_function": verify_dependencies,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Create systemd service",
            "verify_function": verify_systemd_service,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Enable Node.js service",
            "verify_function": verify_service_running,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Create React app directory",
            "verify_function": verify_react_app_directory,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Copy React files",
            "verify_function": verify_react_files_copied,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Install React dependencies",
            "verify_function": verify_react_dependencies,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Build React application",
            "verify_function": verify_react_build_directory,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Create static directory",
            "verify_function": verify_react_static_directory,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Deploy React build",
            "verify_function": verify_react_build_deployed,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Configure Nginx",
            "verify_function": verify_nginx_config,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Enable Nginx site",
            "verify_function": verify_nginx_site_enabled,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Remove default site",
            "verify_function": verify_nginx_default_site_removed,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Nginx service status",
            "verify_function": verify_nginx_running,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "API accessibility",
            "verify_function": verify_api_proxy,
            "args": (ec2_host,),
            "maximum_marks": 1
        },
        {
            "testid": "React frontend accessibility",
            "verify_function": verify_react_frontend,
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

    overall['data'] = data
    with open('evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    os.chmod('inventory/ansible.pem', 0o400)
    main()