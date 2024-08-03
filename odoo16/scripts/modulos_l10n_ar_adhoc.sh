#!/bin/bash
cd /opt/odoo16/extra-addons-l10n_ar

## factura electronica PyAfipWS
#git clone -b py3k https://github.com/pyar/pyafipws.git /opt/odoo16/extra-addons-l10n_ar/pyafipws
#pip3 install -r /opt/odoo16/extra-addons-l10n_ar/pyafipws/requirements.txt
#python3 /opt/odoo16/extra-addons-l10n_ar/pyafipws/setup.py install
#mkdir /opt/odoo16/extra-addons-l10n_ar/pyafipws/cache
#chmod -R 777 /opt/odoo16/extra-addons-l10n_ar/pyafipws/cache
#chmod -R 777 /usr/local/lib/python3.9/dist-packages/PyAfipWs-3.9.0-py3.9.egg/pyafipws

## Localizacion codize/a2 informa cambiar este valor
sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf

## adhoc l10n_ar
git clone -b 16.0 https://github.com/ingadhoc/odoo-argentina /opt/odoo16/extra-addons-l10n_ar/odoo-argentina
git clone -b 16.0 https://github.com/ingadhoc/odoo-argentina-ce /opt/odoo16/extra-addons-l10n_ar/odoo-argentina-ce
git clone -b 16.0 https://github.com/ingadhoc/argentina-sale /opt/odoo16/extra-addons-l10n_ar/argentina-sale
pip3 install -r /opt/odoo16/extra-addons-l10n_ar/odoo-argentina/requirements.txt
pip3 install -r /opt/odoo16/extra-addons-l10n_ar/odoo-argentina-ce/requirements.txt
pip3 install -r /opt/odoo16/extra-addons-l10n_ar/argentina-sale/requirements.txt

## adhoc Account
git clone -b 16.0 https://github.com/ingadhoc/account-payment /opt/odoo16/extra-addons-l10n_ar/account-payment
git clone -b 16.0 https://github.com/ingadhoc/account-invoicing /opt/odoo16/extra-addons-l10n_ar/account-invoicing
git clone -b 16.0 https://github.com/ingadhoc/account-financial-tools /opt/odoo16/extra-addons-l10n_ar/account-financial-tools

## adhoc product (replenishment cost / product planned price)
git clone -b 16.0 https://github.com/ingadhoc/product /opt/odoo16/extra-addons-l10n_ar/product

## adhoc stock
git clone -b 16.0 https://github.com/ingadhoc/stock /opt/odoo16/extra-addons-l10n_ar/stock
#cp -r /opt/odoo16/extra-addons-l10n_ar/adhoc-stock/stock_voucher /opt/odoo16/extra-addons-l10n_ar/stock_voucher
#cp -r /opt/odoo16/extra-addons-l10n_ar/adhoc-stock/delivery_ux /opt/odoo16/extra-addons-l10n_ar/adhoc-delivery_ux
