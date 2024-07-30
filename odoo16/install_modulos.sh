#!/bin/bash

sudo docker exec -it -u root odoo16-app sh /mnt/scripts/updateupgrade.sh
sudo docker exec -it -u root odoo16-app sh /mnt/scripts/modulos_extra.sh
sudo docker exec -it -u root odoo16-app sh /mnt/scripts/modulos_l10n_ar.sh
sudo docker exec -it -u root odoo16-app sh /mnt/scripts/modulos_oca.sh
