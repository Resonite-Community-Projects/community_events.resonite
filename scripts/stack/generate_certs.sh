#!/bin/sh
set -e

CERT_DIR="/certs_shared"
mkdir -p "$CERT_DIR"

# Generate config
cat > "$CERT_DIR/cert_san.cnf" <<'EOF'
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = official.dev.resonite-communities.com

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = official.dev.resonite-communities.com
DNS.2 = dev.resonite-communities.com
EOF

# Generate cert
openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/official.key" \
    -out "$CERT_DIR/official.crt" \
    -config "$CERT_DIR/cert_san.cnf" \
    -extensions req_ext

# Make full bundle (self-signed + system CAs)
cat /etc/ssl/certs/ca-certificates.crt "$CERT_DIR/official.crt" > "$CERT_DIR/full_ca_bundle.crt"

echo "Certificates generated in $CERT_DIR"
