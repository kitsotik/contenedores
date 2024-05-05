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

## Adhoc l10n_ar
git clone -b 17.0 https://github.com/ingadhoc/odoo-argentina /mnt/extra-addons/odoo-argentina
git clone -b 17.0 https://github.com/ingadhoc/odoo-argentina-ce /mnt/extra-addons/odoo-argentina-ce
git clone -b 17.0 https://github.com/ingadhoc/argentina-sale /mnt/extra-addons/argentina-sale

pip3 install -r /mnt/extra-addons/odoo-argentina/requirements.txt
pip3 install -r /mnt/extra-addons/argentina-sale/requirements.txt
pip3 install -r /mnt/extra-addons/odoo-argentina-ce/requirements.txt

## Adhoc Account
git clone -b 17.0 https://github.com/ingadhoc/account-payment /mnt/extra-addons/account-payment
git clone -b 17.0 https://github.com/ingadhoc/account-invoicing /mnt/extra-addons/account-invoicing
git clone -b 17.0 https://github.com/ingadhoc/account-financial-tools /mnt/extra-addons/account-financial-tools
