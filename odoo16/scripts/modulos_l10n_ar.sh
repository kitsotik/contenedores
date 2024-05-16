#!/bin/bash

## factura electronica PyAfipWS
git clone -b py3k https://github.com/pyar/pyafipws.git /mnt/extra-addons/pyafipws
pip3 install -r /mnt/extra-addons/pyafipws/requirements.txt
cd /mnt/extra-addons/pyafipws
python3 /mnt/extra-addons/pyafipws/setup.py install
mkdir /mnt/extra-addons/pyafipws/cache
chmod -R 777 /mnt/extra-addons/pyafipws/cache
chmod -R 777 /usr/local/lib/python3.9/dist-packages/PyAfipWs-3.9.0-py3.9.egg/pyafipws

## Localizacion codize/a2 informa cambiar este valor
sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf

## Adhoc l10n_ar
git clone -b 16.0 https://github.com/ingadhoc/odoo-argentina /mnt/extra-addons/adhoc-odoo-argentina
git clone -b 16.0 https://github.com/ingadhoc/odoo-argentina-ce /mnt/extra-addons/adhoc-odoo-argentina-ce
git clone -b 16.0 https://github.com/ingadhoc/argentina-sale /mnt/extra-addons/adhoc-argentina-sale
pip3 install -r /mnt/extra-addons/adhoc-odoo-argentina/requirements.txt
pip3 install -r /mnt/extra-addons/adhoc-odoo-argentina-ce/requirements.txt
pip3 install -r /mnt/extra-addons/adhoc-argentina-sale/requirements.txt

## Adhoc Account
git clone -b 16.0 https://github.com/ingadhoc/account-payment /mnt/extra-addons/adhoc-account-payment
git clone -b 16.0 https://github.com/ingadhoc/account-invoicing /mnt/extra-addons/adhoc-account-invoicing
git clone -b 16.0 https://github.com/ingadhoc/account-financial-tools /mnt/extra-addons/adhoc-account-financial-tools

## Adhoc product (replenishment cost / product planned price)
git clone -b 16.0 https://github.com/ingadhoc/product /mnt/extra-addons/adhoc-product

## Adhoc stock
git clone -b 16.0 https://github.com/ingadhoc/stock /mnt/extra-addons/adhoc-stock
cp -r /mnt/extra-addons/adhoc-stock/stock_voucher /mnt/extra-addons/adhoc-stock_voucher
cp -r /mnt/extra-addons/adhoc-stock/delivery_ux /mnt/extra-addons/adhoc-delivery_ux
