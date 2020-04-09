#!/bin/bash

echo "Setup NETCONF over TLS with x.509 authentication"
echo "================================================"
sleep 2
echo "Create, sign, and install our own CA and key"
echo "Following the GnuTLS manual, create a certificate authority with certtool:"
certtool --generate-privkey --outfile x509-ca-key.pem
echo 'cn = GnuTLS test CA' > ca.tmpl
echo 'ca' >> ca.tmpl
echo 'cert_signing_key' >> ca.tmpl
certtool --generate-self-signed --load-privkey x509-ca-key.pem \
         --template ca.tmpl --outfile x509-ca.pem

echo "Generate the unencrypted server key:"
certtool --generate-privkey --outfile x509-server-key.pem

echo "Sign the key with an example CA. For this example we set the dns_name to our localhost name:"
echo 'organization = GnuTLS test server' > server.tmpl
echo 'cn = test.gnutls.org' >> server.tmpl
echo 'expiration_days = -1' >> server.tmpl
echo 'tls_www_server' >> server.tmpl
echo 'encryption_key' >> server.tmpl
echo 'signing_key' >> server.tmpl
echo 'dns_name = localhost' >> server.tmpl
certtool --generate-certificate --load-privkey x509-server-key.pem \
         --load-ca-certificate x509-ca.pem --load-ca-privkey x509-ca-key.pem \
         --template server.tmpl --outfile x509-server.pem

echo "For this demo we create an empty Certificate Revocation List (CRL):"
echo "crl_next_update = 42" > crl.tmpl
echo 'crl_number = 7' >> crl.tmpl
certtool --generate-crl --load-ca-privkey x509-ca-key.pem --load-ca-certificate x509-ca.pem \
         --outfile crl.pem --template crl.tmpl

echo "Build the demo and start ConfD"
EXTRA_LIBS=-lgnutls make all

echo "Setup RESTCONF X.509 authentication storing TLS data in ConfD's CDB"
echo "==================================================================="
sleep 2
echo "Generate two root CA private key and certificate (PKCS#8 encoded)"
openssl req -x509 -newkey rsa:2048 -nodes -subj "/CN=localhost" \
        -keyout root-ca-key-1.pem -out root-ca-cert-1.pem
echo "Generate PKCS#8 unencrypted private key, certificate request (CSR), and certificate private key"
openssl genpkey -algorithm rsa -pkeyopt rsa_keygen_bits:2048 \
        -out localhost.key.pem
echo "Certificate request"
openssl req -new -sha256 -key localhost.key.pem -subj "/CN=localhost" \
        -out localhost.csr.pem
echo "Signed public key certificate"
openssl x509 -req -CA root-ca-cert-1.pem  -CAkey root-ca-key-1.pem \
        -CAcreateserial -sha256 \
        -in localhost.csr.pem -out localhost.cert.pem

echo "Generate the TLS key config"
echo "See CONFD_DIR/src/confd/yang/tailf-tls.yang for details"
echo "<?xml version=\"1.0\"?>
<config xmlns=\"http://tail-f.com/ns/config/1.0\">
  <tls xmlns=\"http://tail-f.com/ns/tls\">
        <certificate>
          <cert-data>" > ./confd-cdb/tls_data_nopw.xml
cat localhost.cert.pem >> ./confd-cdb/tls_data_nopw.xml
echo "          </cert-data>
        </certificate>
        <private-key>
          <key-data>" >> ./confd-cdb/tls_data_nopw.xml
cat localhost.key.pem >> ./confd-cdb/tls_data_nopw.xml
echo "          </key-data>
         </private-key>
         <ca-certificates>
            <name>rsa-1</name>
            <cacert-data>" >> ./confd-cdb/tls_data_nopw.xml
cat root-ca-cert-1.pem >> ./confd-cdb/tls_data_nopw.xml
echo "            </cacert-data>
        </ca-certificates>
     </tls>
    </config>" >> ./confd-cdb/tls_data_nopw.xml

# Start ConfD and the CDB subscriber example application
echo "Start ConfD"
make start
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -c "wait-start 2"; ecode=$?; done;

echo "Start the CDB subscriber example application"
./dhcpd_conf

echo "Start our TLS <--> NETCONF relay demo"
echo "====================================="
sleep 2
./tls-x509-subsys

echo "We can now for example use the gnutls-cli program to set up a TLS connection to our NETCONF TLS server"
gnutls-cli -p 6513 --x509cafile x509-ca.pem localhost <<< $(cat cmd-set-dhcp-defaultLeaseTime-1h.xml)

echo "The NETCONF TLS communication is logged in the netconf.trace file"
echo "================================================================="
sleep 2
cat netconf.trace
sleep 2

echo "To demo our RESTCONF TLS setup we do a quick sanity test using the self-signed certificate"
echo "=========================================================================================="
sleep 2
curl -kvu admin:admin -H "Accept: application/yang-data+json" https://localhost:8888/restconf/data/dhcpd:dhcp

echo "The resulting ConfD developer log:"
echo "=================================="
sleep 2
tail -n 500 -F devel.log
