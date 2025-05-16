FROM ubuntu:22.04 as ubuntu-stage

# Install common packages + Ansible/SSH dependencies
RUN yes | unminimize
RUN apt-get update -y && apt-get install -y software-properties-common language-pack-en-base debconf-utils curl
RUN apt-get update -y && apt-get install -y \
    net-tools wget nano vim less gnupg \
    openssh-client rsync \
    iproute2 python3 python3-pip \
    man-db zip \
    ca-certificates

# Install Ansible via pip and upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install boto3 requests ansible

# Install Terraform
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y terraform

# Setup environment and directories
ENV INSTRUCTOR_SCRIPTS="/home/.evaluationScripts"
ENV LAB_DIRECTORY="/home/labDirectory"
ENV PATH="/home/.evaluationScripts:${PATH}"
ENV TERM=xterm-256color
RUN mkdir -p /home/labDirectory /home/.evaluationScripts

# Shell configuration
RUN echo "cd /home/labDirectory" > /root/.bashrc && \
    echo "alias ls='ls --color=always'" >> /root/.bashrc && \
    echo "rm -f \`find /home -type f -name \"._*\"\`" >> /root/.bashrc

# Uncomment these if you want to bake content into the image
COPY labDirectory /home/labDirectory
COPY .evaluationScripts /home/.evaluationScripts

WORKDIR /home
CMD [ "/bin/bash", "-c", "while :; do sleep 10; done" ]