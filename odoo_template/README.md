

# Instalación y Configuración Inicial

## Preparación Inicial
1. Instalar docker -> https://docs.docker.com/get-docker/
2. Instalar docker-compose -> https://docs.docker.com/compose/install/

## Instalación de Odoo con docker
1. Descargar el repositorio
~~~
git clone https://github.com/escuelafullstack/template_odoo_docker_compose.git
~~~
2. Ingresar a la carpeta 
~~~
cd template_odoo_docker_compose
~~~
3. Crear archivo .env y docker-compose.yaml
~~~
cp copy.env .env
cp copy.docker-compose.yaml docker-compose.yaml
~~~
4. Editar parámetros de .env
~~~
Ejemplo:
WEB_HOST=efs_odoo_empresa1 
WEB_PORT=8087
~~~
5. Opcional: Editar docker-compose.yaml, esto siempre y cuando se requiera añadir nuevos servicios o modificar parámetros.
6. Ejecutar docker-compose
~~~
docker-compose up -d
docker-compose up --build
~~~
7. Si cambias el dockerfile
sudo docker-compose up --build -V --force-rm --no-cache 


#docker-compose -f dc-odoo13-gimaq.yml up -d
#sudo docker exec -t -u root odoo-rproxy mkdir /etc/nginx/sites-enabled
#sudo docker exec -t -u root odoo-rproxy ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/odoo 
#exit
#ngixn -t *check sintax
#nginx -s reload *restart
#cambiar la ip local en el conf del nginx
#usar contraseña del conf de odoo para crear db
#instalar modulos basico, instalar localizacion




