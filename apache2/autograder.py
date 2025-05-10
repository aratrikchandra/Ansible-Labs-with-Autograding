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
    
    if 'apacheserver' in config:
        for host in config['apacheserver']:
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
        raise ValueError("EC2 host not found in inventory.ini under [apacheserver] group.")
    
    return ec2_host, user, key_path

def run_remote_command(command, key_path, user, host):
    """Execute a command on the EC2 instance via SSH"""
    ssh_cmd = f"ssh -i {key_path} -o StrictHostKeyChecking=no {user}@{host} '{command}'"
    return execute_command(ssh_cmd)

def verify_inventory_config(key_path, user, host):
    """Verify SSH connectivity using inventory details."""
    out, err = run_remote_command("echo ok", key_path, user, host)
    if out == 'ok':
        return True, "SSH connection successful using inventory details."
    else:
        return False, f"SSH connection failed: {err or 'Unknown error'}"

def verify_apache_installed(key_path, user, host):
    """Check if Apache2 is installed."""
    out, err = run_remote_command("apache2 -v", key_path, user, host)
    if out and 'Apache/2' in out:
        return True, f"Apache2 installed: {out.splitlines()[0]}"
    return False, "Apache2 is not installed."

def verify_apache_service(key_path, user, host):
    """Check if Apache2 service is active."""
    out, err = run_remote_command("systemctl is-active apache2", key_path, user, host)
    if out == 'active':
        return True, "Apache2 service is running."
    return False, f"Apache2 service is not active. Status: {out}"

def verify_index_html(key_path, user, host):
    """Verify index.html is correctly deployed."""
    # Check file exists
    out, err = run_remote_command("[ -f /var/www/html/index.html ] && echo exists", key_path, user, host)
    if out != 'exists':
        return False, "index.html not found in /var/www/html/."
    
    # Check ownership
    out, err = run_remote_command("stat -c '%U:%G' /var/www/html/index.html", key_path, user, host)
    if out != 'ubuntu:ubuntu':
        return False, f"Incorrect ownership: {out}. Expected ubuntu:ubuntu."
    
    # Check permissions
    out, err = run_remote_command("stat -c '%a' /var/www/html/index.html", key_path, user, host)
    if out != '644':
        return False, f"Incorrect permissions: {out}. Expected 644."
    
    return True, "index.html is correctly deployed."

def verify_website_content(host):
    """Check if website serves the correct content."""
    try:
        response = requests.get(f"http://{host}", timeout=5)
        if response.status_code != 200:
            return False, f"HTTP status code {response.status_code} received."
        content = response.text
        if '<h1>I am learning Ansible with Vlab</h1>' in content:
            return True, "Website content is correct."
        else:
            return False, "Website content does not match expected text."
    except Exception as e:
        return False, f"Failed to access website: {str(e)}"

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

    # Run Ansible playbook first
    playbook_cmd = f"ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory/inventory.ini playbook.yml"
    pb_out, pb_err = execute_command(playbook_cmd)
    
    test_cases = [
        {
            "testid": "Inventory Configuration",
            "verify_function": verify_inventory_config,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Apache2 Installation",
            "verify_function": verify_apache_installed,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Apache Service Running",
            "verify_function": verify_apache_service,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "index.html Deployment",
            "verify_function": verify_index_html,
            "args": (key_path, user, ec2_host),
            "maximum_marks": 1
        },
        {
            "testid": "Website Accessibility",
            "verify_function": verify_website_content,
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