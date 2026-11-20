#!/bin/sh
# Run only inside the disposable build test containers.
set -eu
mkdir -p /etc/apache2/conf
cat > /etc/apache2/conf/httpd.conf <<'EOF'
<VirtualHost *:80>
    ServerName bolt.example
    DocumentRoot /home/bolt/public_html
</VirtualHost>
EOF
/bolt_linux_amd64 --version
/bolt_linux_amd64 --help
test "$(/bolt_linux_amd64 status bolt.example)" = "[+] Domain bolt.example is UNLOCKED"
