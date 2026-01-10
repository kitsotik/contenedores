sudo sh ./scripts/addons_extra.sh
sudo sh ./scripts/addons_l10n_ar_adhoc.sh
sudo sh ./scripts/addons_oca.sh
sudo sh ./scripts/addons_omyg.sh
sudo sh ./scripts/fix_l10n_ar_account_reports.sh
sudo sh ./scripts/fix_odoo18_translation_defaults.sh
sudo chown -R oem:oem addons-extra
sudo chown -R oem:oem addons-l10n_ar
sudo chown -R oem:oem addons-oca
sudo chown -R oem:oem addons-omyg
sudo docker compose up -d --build



