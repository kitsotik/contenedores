#!/bin/bash

sudo rm -R extra-addons/*
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_comunes.sh
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_adhoc.sh
