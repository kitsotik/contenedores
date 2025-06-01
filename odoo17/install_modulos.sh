#!/bin/bash

if [ -z "$1" ]; then
    echo "No se proporcionó ninguna versión como argumento."
    exit 1
else
    echo "Se recibió la versión: $1"
fi

# Almacena el argumento como la versión
VERSION=$1

sudo docker exec -it -u root odoo-app sh /mnt/scripts/updateupgrade.sh
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_oca.sh $VERSION
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_extra.sh $VERSION
sudo docker exec -it -u root odoo-app sh /mnt/scripts/modulos_l10n_ar_adhoc.sh $VERSION
