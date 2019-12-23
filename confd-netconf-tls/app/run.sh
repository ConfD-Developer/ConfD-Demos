#!/bin/bash

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
EXTRA_LIBS=-lgnutls make all start
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -c "wait-start 2"; ecode=$?; done;

echo "Start the subscriber example program"
./dhcpd_conf &

echo "Start our TLS <--> NETCONF relay demo"
./tls-x509-subsys

echo "We can now for example use the gnutls-cli program to set up a TLS connection to our NETCONF TLS server:"
gnutls-cli -p 6513 --x509cafile x509-ca.pem localhost <<< $(cat cmd-set-dhcp-defaultLeaseTime-1h.xml)

echo "The NETCONF communication is logged in the netconf.trace file"
tail -n 500 -F netconf.trace
