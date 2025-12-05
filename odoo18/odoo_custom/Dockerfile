ARG ODOO_VERSION=18
FROM odoo:${ODOO_VERSION}

USER root

# 1. Copiamos el requirements desde la raíz del contexto
COPY ./requirements.txt /etc/odoo/requirements.txt

COPY addons-l10n_ar/ /tmp/community_addons/

# 2. Consolidamos todos los requirements.txt que existan dentro de los módulos
RUN find /tmp/community_addons/ -type f -name 'requirements.txt' -exec cat {} + >> /tmp/all_requirements.txt

# 2. Instalamos SOLO las librerías del sistema necesarias para compilar otras cosas
#    Eliminamos libpq-dev para evitar el conflicto.
RUN apt-get update  \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    git \
    gcc \
    swig \
    unzip \
    curl \
    build-essential \
    # Dependencias de librerías Python (para Pillow, lxml, etc.)
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    libtiff5-dev \
    libopenjp2-7-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-m2crypto \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Instalamos dependencias de Python
#    Asegúrate de agregar 'psycopg2-binary' a tu requirements.txt si no está.
#    Si usas 'pandas' u otra, agrégala aquí.
# Dockerfile: Línea 50
RUN pip3 install --no-cache-dir -r /etc/odoo/requirements.txt --break-system-packages 
RUN pip3 install --upgrade reportlab --break-system-packages
RUN pip3 install rlPyCairo --break-system-packages
RUN pip3 install astor --break-system-packages
RUN pip3 install paramiko pysftp --break-system-packages 
RUN pip3 install setuptools wheel --break-system-packages

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