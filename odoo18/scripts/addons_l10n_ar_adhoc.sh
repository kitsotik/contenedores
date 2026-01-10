#!/bin/bash

## adhoc l10n_ar
git clone -b 18.0 https://github.com/ingadhoc/odoo-argentina ./addons-l10n_ar/odoo-argentina
git clone -b 18.0 https://github.com/ingadhoc/odoo-argentina-ce ./addons-l10n_ar/odoo-argentina-ce
git clone -b 18.0 https://github.com/ingadhoc/argentina-sale ./addons-l10n_ar/argentina-sale

#pip3 install -r ./addons-l10n_ar/odoo-argentina-ce/requirements.txt --break-system-packages
#pip3 install -r ./addons-l10n_ar/argentina-sale/requirements.txt --break-system-packages

## adhoc account
git clone -b 18.0 https://github.com/ingadhoc/account-payment ./addons-l10n_ar/account-payment
git clone -b 18.0 https://github.com/ingadhoc/account-invoicing ./addons-l10n_ar/account-invoicing
git clone -b 18.0 https://github.com/ingadhoc/account-financial-tools ./addons-l10n_ar/account-financial-tools

## adhoc product (replenishment cost / product planned price)
git clone -b 18.0 https://github.com/ingadhoc/product ./addons-l10n_ar/product

## adhoc stock
git clone -b 18.0 https://github.com/ingadhoc/stock ./addons-l10n_ar/stock
#cp -r ./addons-l10n_ar/adhoc-stock/stock_voucher ./addons-l10n_ar/stock_voucher
#cp -r ./addons-l10n_ar/adhoc-stock/delivery_ux ./addons-l10n_ar/adhoc-delivery_ux

## adhoc sale
git clone -b 18.0 https://github.com/ingadhoc/sale ./addons-l10n_ar/sale

## adhoc multicompany
git clone -b 18.0 https://github.com/ingadhoc/multi-company ./addons-l10n_ar/multi-company
cp -r ./addons-l10n_ar/multi-company/account_multicompany_ux ./addons-l10n_ar/account_multicompany_ux