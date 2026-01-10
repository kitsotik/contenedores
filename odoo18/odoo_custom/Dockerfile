ARG ODOO_VERSION=18
FROM odoo:${ODOO_VERSION}

USER root

#Copiamos el requirements desde la raíz del contexto
COPY ./requirements.txt /etc/odoo/requirements.txt

COPY addons-l10n_ar/ /tmp/community_addons/

#Consolidamos todos los requirements.txt que existan dentro de los módulos
RUN find /tmp/community_addons/ -type f -name 'requirements.txt' -exec cat {} + >> /tmp/all_requirements.txt

## Instalar dependencias necesarias
RUN apt-get update \
 && apt-get install -y git gcc swig python3-m2crypto unzip curl python3-venv \
 && curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
 && python3 get-pip.py --break-system-packages --ignore-installed\
 && rm get-pip.py

RUN pip install setuptools==69.0.3 wheel --break-system-packages 

## Instalar pyfafipws versión 2025 
RUN pip install git+https://github.com/reingart/pyafipws.git@2025 --break-system-packages

## Parche para SSL
RUN mkdir -p /usr/local/lib/python3.12/dist-packages/pyafipws/cache
RUN chown -R odoo:odoo /usr/local/lib/python3.12/dist-packages/pyafipws/cache
RUN sed  -i "s/CipherString = DEFAULT@SECLEVEL=2/#CipherString = DEFAULT@SECLEVEL=2/" /etc/ssl/openssl.cnf

# Instala los paquetes de locales para evitar la advertencia de Perl/Locale / Configura y genera la locale en_US.UTF-8 (común en entornos Odoo)
RUN apt update \
    && apt install -y locales \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && export LANG="en_US.UTF-8" \
    && export LC_ALL="en_US.UTF-8" \
    && apt autoremove -y \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

USER odoo