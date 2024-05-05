#!/bin/bash

sudo rm -R addons_custom/*
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_comunes.sh
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_adhoc.sh
