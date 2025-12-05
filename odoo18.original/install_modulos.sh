#!/bin/bash

sudo docker exec -it -u root odoo-app sh /mnt/scripts/updateupgrade.sh
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_extra.sh
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_l10n_ar_adhoc.sh
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_oca.sh
