## Run playbook

```bash
ansible-playbook --inventory inventory/hosts playbook-uninstall.yml
```


## How to find apache is installed or not 

```
type -a apache2 
```


## SSH to EC2 instance

```
ssh -i /Users/rahulwagh/.ssh/aws_ec2_terraform ubuntu@ec2-3-74-153-166.eu-central-1.compute.amazonaws.com

```
ansible-playbook -i inventory/inventory.ini playbook.yml