#!/bin/bash

apt update
apt upgrade -y
pip3 install --upgrade pip
apt install -y git build-essential python3-m2crypto
pip install --upgrade requests urllib3 chardet




