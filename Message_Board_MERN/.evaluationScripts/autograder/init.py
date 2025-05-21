import json
import os
import shutil
import subprocess

def main():
    # Load credentials from data.json
    with open('data.json', 'r') as f:
        credentials = json.load(f)
    
    # Replace placeholders in main.tf
    with open('terraform/main.tf', 'r') as f:
        main_tf = f.read()
    
    main_tf = main_tf.replace(
        "<Replace with Instructor Access key ID>",
        credentials["Instructor Access key ID"]
    ).replace(
        "<Replace with Instructor Secret access key>",
        credentials["Instructor Secret access key"]
    )
    
    with open('terraform/main.tf', 'w') as f:
        f.write(main_tf)

    # Apply Terraform configuration
    original_dir = os.getcwd()
    os.chdir('terraform')
    
    try:
        subprocess.run(["terraform", "init"], check=True)
        
        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Terraform error: {e}")
        os.chdir(original_dir)
        return
    finally:
        os.chdir(original_dir)

    # Read Terraform outputs
    with open('terraform/terraform.tfstate', 'r') as f:
        tf_state = json.load(f)
    
    outputs = tf_state.get('outputs', {})
    public_ip = outputs['public_ip']['value']
    private_key_path = outputs['private_key_file']['value']

    # Copy SSH key to inventory
    key_src = os.path.join('terraform', private_key_path)
    key_dest = os.path.join('inventory', 'ansible.pem')
    shutil.copy(key_src, key_dest)
    os.chmod(key_dest, 0o600)

    # Update inventory file
    with open('inventory/inventory.ini', 'r') as f:
        inventory = f.read()
    
    inventory = inventory.replace("<public-ip>", public_ip)
    
    with open('inventory/inventory.ini', 'w') as f:
        f.write(inventory)

    print("Setup completed successfully!")
    print(f"Public IP: {public_ip}")
    print(f"SSH Key: {key_dest}")

if __name__ == "__main__":
    main()