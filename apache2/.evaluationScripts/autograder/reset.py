import os
import re
import subprocess
import shutil

def reset_environment():
    # Store original working directory
    original_dir = os.getcwd()
    
    try:
        # Destroy Terraform infrastructure
        os.chdir('terraform')
        subprocess.run(["terraform", "init"], check=True)
        destroy_process = subprocess.run(["terraform", "destroy", "-auto-approve"], capture_output=True, text=True)
        
        if destroy_process.returncode != 0:
            print("Error during Terraform destroy:")
            print(destroy_process.stderr)
            return False
    finally:
        os.chdir(original_dir)

    # Clean up generated files
    generated_files = [
        ('inventory', 'ansible.pem'),
    ]

    for folder, filename in generated_files:
        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed: {file_path}")

    # Reset inventory file
    inventory_content = """[apacheserver]
<public-ip> ansible_user=ubuntu ansible_ssh_private_key_file=inventory/ansible.pem
"""
    with open(os.path.join('inventory', 'inventory.ini'), 'w') as f:
        f.write(inventory_content)
    print("Reset inventory.ini to initial state")

    # Restore main.tf credentials to placeholders
    main_tf_path = os.path.join('terraform', 'main.tf')
    with open(main_tf_path, 'r') as f:
        content = f.read()

    # Use regex to replace credentials
    content = re.sub(
        r'access_key\s*=\s*"[^"]*"',
        'access_key = "<Replace with Instructor Access key ID>"',
        content
    )
    content = re.sub(
        r'secret_key\s*=\s*"[^"]*"',
        'secret_key = "<Replace with Instructor Secret access key>"',
        content
    )

    with open(main_tf_path, 'w') as f:
        f.write(content)
    print("Restored main.tf to initial configuration")

    # Clean Terraform state files
    terraform_files = [
        'terraform.tfstate',
        'terraform.tfstate.backup',
        '.terraform.lock.hcl',
        '.terraform'
    ]
    
    for file in terraform_files:
        path = os.path.join('terraform', file)
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    
    print("Cleaned up Terraform state files")

    return True

if __name__ == "__main__":
    print("Starting environment reset...")
    if reset_environment():
        print("Reset completed successfully!")
    else:
        print("Reset completed with errors. Check output for details.")