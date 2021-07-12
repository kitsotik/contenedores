FROM odoo:latest 

LABEL MAINTAINER kitsotik <kitsotik@gimaq.com.ar>
USER root

RUN pip3 install wheel
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y apt-utils
RUN apt-get install -y git python-m2crypto gcc libssl-dev swig python3-dev 


#RUN git clone https://github.com/ctmil/odoo-argentina/ -b 14.0 /mnt/addons-custom
#RUN cd /mnt/addons-custom
#RUN pip3 install --upgrade pip
#RUN pip3 install -r /mnt/addons-custom/moldeo/requirements.txt
#RUN apt-get install python-

#COPY /scripts/localizacion-moldeo.sh /usr/local/bin/
#ENTRYPOINT []




# Choose and name our temporary image.
#FROM alpine as intermediate
#LABEL stage=intermediate
#RUN apk update && apk upgrade && apk add --no-cache bash git
#WORKDIR /app
#RUN git clone https://github.com/ctmil/odoo-argentina/ -b 14.0 /app

