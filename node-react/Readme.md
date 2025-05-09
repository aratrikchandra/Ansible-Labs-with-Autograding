OS: Ubuntu 22.04 LTS

Instance Type: t2.micro

Security Group:

Inbound Rules:

SSH (port 22) - Your IP

Custom TCP (port 5000) - 0.0.0.0/0

Key Pair: Create/use an SSH key pair for authentication


ansible-playbook -i inventory/inventory.ini playbook.yml