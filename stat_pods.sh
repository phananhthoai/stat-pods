#!/usr/bin/env bash

set -ex


HOST=${1}

sudo apt-get update
sudo pip3 install -r requirements.txt

microk8s.config | sudo tee  /root/config

cat <<EOF | sudo tee  /etc/systemd/system/stat_pods.service > /dev/null
[Unit]
Description=Stat Pods

[Service]
Type=simple
ExecStart=python3 /opt/stat_pods/main.py

[Install]
WantedBy=multi-user.target

EOF

cat namespace | sudo tee /usr/local/bin/namespace

sudo chmod +x /usr/local/bin/namespace

cat main.py | sudo tee /opt/stat_pods/main.py

sudo sed -i -E "s/(.+host\=\")[0.]+(\".+)/\1"${HOST}"\2/g" /opt/stat_pods/main.py
