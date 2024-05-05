#!/bin/bash

## factura electronica PyAfipWS
git clone -b py3k https://github.com/pyar/pyafipws.git /mnt/extra-addons/pyafipws
pip3 install -r /mnt/extra-addons/pyafipws/requirements.txt
cd /mnt/extra-addons/pyafipws
python3 /mnt/extra-addons/pyafipws/setup.py install
mkdir /mnt/extra-addons/pyafipws/cache
chmod -R 777 /mnt/extra-addons/pyafipws/cache
cd /mnt

## Localizacion codize informa cambiar este valor
sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf

## A2 l10n_ar
git clone -b 16.0 https://github.com/a2systems/odoo-argentina /mnt/extra-addons/odoo-argentina
pip3 install -r /mnt/extra-addons/odoo-argentina/requirements.txt

