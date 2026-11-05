#!/bin/bash
set -e

# 1. Add 2GB Swap Memory (Prevent MySQL OOM crashes on t3.micro)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 2. System update and package installation
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx mysql-server php-fpm php-mysql php-curl php-gd   php-mbstring php-xml php-zip php-intl unzip curl ed

# 3. Enable & start core services
systemctl enable --now nginx
systemctl enable --now mysql

# 4. Automatically locate active PHP-FPM socket path
PHP_SOCKET=$(ls /run/php/php*-fpm.sock | head -n 1)

# 5. Provision MySQL database & dedicated application user
DB_NAME="wordpress"
DB_USER="wpuser"
DB_PASS="SecureLabPass2026!"

mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# 6. Download and deploy WordPress core files
cd /tmp
curl -s -O https://wordpress.org/latest.tar.gz
tar -xzf latest.tar.gz
rm -rf /var/www/html/*
cp -r wordpress/* /var/www/html/

# 7. Apply standard production ownership & permissions
chown -R www-data:www-data /var/www/html
find /var/www/html -type d -exec chmod 755 {} \;
find /var/www/html -type f -exec chmod 644 {} \;

# 8. Configure Nginx Virtual Host for WordPress
cat <<EOF > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.php index.html index.htm;

    server_name _;

    location / {
        try_files \$uri \$uri/ /index.php?\$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:${PHP_SOCKET};
    }

    location ~ /\.ht {
        deny all;
    }
}
EOF

# 9. Verify syntax and reload Nginx
nginx -t && systemctl reload nginx

# 10. Configure wp-config.php with database credentials
cd /var/www/html
cp wp-config-sample.php wp-config.php
sed -i "s/database_name_here/${DB_NAME}/" wp-config.php
sed -i "s/username_here/${DB_USER}/" wp-config.php
sed -i "s/password_here/${DB_PASS}/" wp-config.php

chown www-data:www-data wp-config.php
chmod 640 wp-config.php

echo "WordPress automated installation complete!"
