#!/bin/bash

## adhoc l10n_ar
git clone -b 18.0 https://github.com/ingadhoc/odoo-argentina /opt/odoo/extra-addons-l10n_ar/odoo-argentina
git clone -b 18.0 https://github.com/ingadhoc/odoo-argentina-ce /opt/odoo/extra-addons-l10n_ar/odoo-argentina-ce
git clone -b 18.0 https://github.com/ingadhoc/argentina-sale /opt/odoo/extra-addons-l10n_ar/argentina-sale
pip3 install -r /opt/odoo/extra-addons-l10n_ar/odoo-argentina/requirements.txt --break-system-packages
pip3 install -r /opt/odoo/extra-addons-l10n_ar/odoo-argentina-ce/requirements.txt --break-system-packages
pip3 install -r /opt/odoo/extra-addons-l10n_ar/argentina-sale/requirements.txt --break-system-packages

## adhoc Account
git clone -b 18.0 https://github.com/ingadhoc/account-payment /opt/odoo/extra-addons-l10n_ar/account-payment
git clone -b 18.0 https://github.com/ingadhoc/account-invoicing /opt/odoo/extra-addons-l10n_ar/account-invoicing
git clone -b 18.0 https://github.com/ingadhoc/account-financial-tools /opt/odoo/extra-addons-l10n_ar/account-financial-tools

## adhoc product (replenishment cost / product planned price)
git clone -b 18.0 https://github.com/ingadhoc/product /opt/odoo/extra-addons-l10n_ar/product

## adhoc stock
git clone -b 18.0 https://github.com/ingadhoc/stock /opt/odoo/extra-addons-l10n_ar/stock
#cp -r /opt/odoo/extra-addons-l10n_ar/adhoc-stock/stock_voucher /opt/odoo/extra-addons-l10n_ar/stock_voucher
#cp -r /opt/odoo/extra-addons-l10n_ar/adhoc-stock/delivery_ux /opt/odoo/extra-addons-l10n_ar/adhoc-delivery_ux

## Instalar pyfafipws versión 2025 
#pip install git+https://github.com/reingart/pyafipws.git@2025 --break-system-packages

## Parche para SSL
#mkdir -p /usr/local/lib/python3.12/dist-packages/pyafipws/cache
#chown -R odoo:odoo /usr/local/lib/python3.12/dist-packages/pyafipws/cache
#sed  -i "s/CipherString = DEFAULT@SECLEVEL=2/#CipherString = DEFAULT@SECLEVEL=2/" /etc/ssl/openssl.cnf


## factura electronica PyAfipWS
#git clone -b py3k https://github.com/pyar/pyafipws.git /opt/odoo/extra-addons-l10n_ar/pyafipws
#pip3 install -r /opt/odoo/extra-addons-l10n_ar/pyafipws/requirements.txt
#python3 /opt/odoo/extra-addons-l10n_ar/pyafipws/setup.py install
#mkdir /opt/odoo/extra-addons-l10n_ar/pyafipws/cache
#chmod -R 777 /opt/odoo/extra-addons-l10n_ar/pyafipws/cache
#chmod -R 777 /usr/local/lib/python3.9/dist-packages/PyAfipWs-3.9.0-py3.9.egg/pyafipws

## Localizacion codize/a2 informa cambiar este valor
#sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf