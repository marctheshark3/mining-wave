#!/bin/bash

# Set variables
DOMAINS=("api.ergominers.com") # Add more domains if needed, space-separated
EMAIL="marctheshark333@gmail.com"
RSA_KEY_SIZE=4096
DATA_PATH="./certbot_data" # Needs to match volume mount point in compose
STAGING=0 # Set to 1 to use Let's Encrypt staging servers for testing

echo "### Creating dummy certificate for $DOMAINS ..."

# Create directories if they don't exist
path="$DATA_PATH/conf/live/$DOMAINS"
mkdir -p "$path"

# Check if dummy certs already exist
if [ -f "$path/privkey.pem" ] && [ -f "$path/fullchain.pem" ]; then
  echo "Dummy certificates already exist. Skipping creation."
else
  # Generate dummy certs
  openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
    -keyout "$path/privkey.pem" \
    -out "$path/fullchain.pem" \
    -subj "/CN=localhost"
fi

echo
echo "### Starting nginx ..."
# Start nginx using the production compose file in detached mode
# Use docker compose instead of docker-compose if that's your command
docker-compose -f docker-compose.prod.yaml up --force-recreate -d nginx

echo
echo "### Deleting dummy certificate for $DOMAINS ..."
rm -Rf "$DATA_PATH/conf/live/$DOMAINS"
rm -Rf "$DATA_PATH/conf/archive/$DOMAINS"
rm -Rf "$DATA_PATH/conf/renewal/${DOMAINS}.conf"

echo
echo "### Requesting Let's Encrypt certificate for $DOMAINS ..."

# Join $DOMAINS to -d args
domain_args=""
for domain in "${DOMAINS[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Select appropriate email arg
case "$EMAIL" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $EMAIL" ;;
esac

# Enable staging mode if needed
if [ $STAGING != "0" ]; then staging_arg="--staging"; fi

# Run certbot container to obtain the certificate
docker-compose -f docker-compose.prod.yaml run --rm --entrypoint " \
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $RSA_KEY_SIZE \
    --agree-tos \
    --force-renewal" certbot

echo
echo "### Reloading nginx ..."
# Reload nginx to pick up the new certificates
docker-compose -f docker-compose.prod.yaml exec nginx nginx -s reload

echo
echo "### Certbot initialization complete!"
echo "### You should now be able to start your full stack with: docker-compose -f docker-compose.prod.yaml up -d" 