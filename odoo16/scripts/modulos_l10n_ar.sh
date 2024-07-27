#!/bin/bash
cd /opt/odoo16/extra-addons

## factura electronica PyAfipWS
#git clone -b py3k https://github.com/pyar/pyafipws.git /opt/odoo16/extra-addons/pyafipws
#pip3 install -r /opt/odoo16/extra-addons/pyafipws/requirements.txt
#python3 /opt/odoo16/extra-addons/pyafipws/setup.py install
#mkdir /opt/odoo16/extra-addons/pyafipws/cache
#chmod -R 777 /opt/odoo16/extra-addons/pyafipws/cache
#chmod -R 777 /usr/local/lib/python3.9/dist-packages/PyAfipWs-3.9.0-py3.9.egg/pyafipws

## Localizacion codize/a2 informa cambiar este valor
sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf

## adhoc l10n_ar
git clone -b 16.0 https://github.com/ingadhoc/odoo-argentina /opt/odoo16/extra-addons/adhoc-odoo-argentina
git clone -b 16.0 https://github.com/ingadhoc/odoo-argentina-ce /opt/odoo16/extra-addons/adhoc-odoo-argentina-ce
git clone -b 16.0 https://github.com/ingadhoc/argentina-sale /opt/odoo16/extra-addons/adhoc-argentina-sale
pip3 install -r /opt/odoo16/extra-addons/adhoc-odoo-argentina/requirements.txt
pip3 install -r /opt/odoo16/extra-addons/adhoc-odoo-argentina-ce/requirements.txt
pip3 install -r /opt/odoo16/extra-addons/adhoc-argentina-sale/requirements.txt

## adhoc Account
git clone -b 16.0 https://github.com/ingadhoc/account-payment /opt/odoo16/extra-addons/adhoc-account-payment
git clone -b 16.0 https://github.com/ingadhoc/account-invoicing /opt/odoo16/extra-addons/adhoc-account-invoicing
git clone -b 16.0 https://github.com/ingadhoc/account-financial-tools /opt/odoo16/extra-addons/adhoc-account-financial-tools

## adhoc product (replenishment cost / product planned price)
git clone -b 16.0 https://github.com/ingadhoc/product /opt/odoo16/extra-addons/adhoc-product

## adhoc stock
git clone -b 16.0 https://github.com/ingadhoc/stock /opt/odoo16/extra-addons/adhoc-stock
#cp -r /opt/odoo16/extra-addons/adhoc-stock/stock_voucher /opt/odoo16/extra-addons/stock_voucher
#cp -r /opt/odoo16/extra-addons/adhoc-stock/delivery_ux /opt/odoo16/extra-addons/adhoc-delivery_ux
