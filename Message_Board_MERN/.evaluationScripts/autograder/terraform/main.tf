provider "aws" {
  access_key = "<Replace with Instructor Access key ID>"
  secret_key = "<Replace with Instructor Secret access key>"
  region     = "us-east-1"
}

# Generate random suffix
resource "random_id" "suffix" {
  byte_length = 4
}

# Generate SSH key pair
resource "tls_private_key" "instance_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS key pair
resource "aws_key_pair" "instance_key" {
  key_name   = "instance-key-${random_id.suffix.hex}"
  public_key = tls_private_key.instance_key.public_key_openssh
}

# Save private key to local file
resource "local_file" "private_key" {
  content         = tls_private_key.instance_key.private_key_pem
  filename        = "${path.module}/instance-key-${random_id.suffix.hex}.pem"
  file_permission = "0600"
}

# Security group configuration
resource "aws_security_group" "web_sg" {
  name        = "web-sg-${random_id.suffix.hex}"
  description = "Allow SSH, HTTP"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EC2 Instance
resource "aws_instance" "web_server" {
  ami             = "ami-0f9de6e2d2f067fca"
  instance_type   = "t2.micro"
  key_name        = aws_key_pair.instance_key.key_name
  security_groups = [aws_security_group.web_sg.name]

  tags = {
    Name = "ubuntu-web-server-${random_id.suffix.hex}"
  }
}

output "public_ip" {
  value = aws_instance.web_server.public_ip
}

output "private_key_file" {
  value = local_file.private_key.filename
}