#!/bin/bash

sudo rm -R extra-addons/*
sudo docker exec -it -u root odoo16-app sh /mnt/scripts/modulos_comunes.sh
sudo docker exec -it -u root odoo16-app sh /mnt/scripts/modulos_l10n_ar.sh
sudo docker exec -it -u root odoo16-app sh /mnt/scripts/modulos_oca.sh
