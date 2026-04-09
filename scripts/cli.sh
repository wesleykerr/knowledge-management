#!/bin/bash
set -e

# ------------------------------------------------------------------------------
# Prepare for the terraform deploy
# ------------------------------------------------------------------------------
COPYFILE_DISABLE=1 tar --format=posix -zcvf /tmp/code.tgz knowledge scripts pyproject.toml .python-version

REMOTE_SCRIPT='
    CODE_DIR="/home/wkerr/knowledge-management-$(uuidgen | cut -c 33-)"
    mkdir -p ${CODE_DIR}
    mv /home/wkerr/code.tgz ${CODE_DIR}/code.tgz
    cd ${CODE_DIR}
    tar -zxf code.tgz
    rm code.tgz

    cd /home/wkerr/
    ln -sfn ${CODE_DIR} /home/wkerr/knowledge-management
    cd /home/wkerr/knowledge-management
    sudo cp scripts/knowledge.service /etc/systemd/system/

    sudo systemctl daemon-reload
    sudo systemctl restart knowledge.service

    # Show service status for verification
    echo "Services status:"
    sudo systemctl status knowledge.service --no-pager || true
'

scp -i ~/.ssh/racknerd /tmp/code.tgz wkerr@172.245.131.124:code.tgz
ssh -t -i ~/.ssh/racknerd wkerr@172.245.131.124 "$REMOTE_SCRIPT"

