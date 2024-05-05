sudo apt-get install software-properties-common
sudo add-apt-repository ppa:certbot/certbot
apt-get update
apt-get install python-certbot-nginx

nginx -t && nginx -s reload

sudo ufw allow 'Nginx Full'
sudo ufw status

cd /etc/nginx/sites-available

sudo nano odoo

sudo certbot --nginx -d tienda.gimaq.com.ar -d tienda.gimaq.com.ar

poner el mail
opciones 2



 listen 443 ssl; # managed by Certbot

    # RSA certificate
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem; # managed by Certbot

    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot

    # Redirect non-https traffic to https
    if ($scheme != "https") {
        return 301 https://$host$request_uri;
    } # managed by Certbot
}


tienda.gimaq.com.ar
93.188.166.80
