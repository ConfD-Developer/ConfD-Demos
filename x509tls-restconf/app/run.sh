#!/bin/bash
echo "Build the simple subscribrer and setup ConfD"
make all

echo "Setup RESTCONF X.509 authentication storing TLS data in ConfD's CDB"
echo "==================================================================="

echo "Generate a root CA private key and certificate (PKCS#8 encoded)"
openssl req -x509 -newkey rsa:2048 -nodes -subj "/CN=localhost" \
        -keyout root-ca-key-1.pem -out root-ca-cert-1.pem
echo "Generate a PKCS#8 unencrypted private key"
openssl genpkey -algorithm rsa -pkeyopt rsa_keygen_bits:2048 \
        -out server.key.pem
echo "Certificate request"
openssl req -new -sha256 -key server.key.pem -subj "/CN=localhost" \
        -out server.csr.pem
echo "Signed public key certificate"
openssl x509 -req -CA root-ca-cert-1.pem  -CAkey root-ca-key-1.pem \
        -CAcreateserial -sha256 \
        -in server.csr.pem -out server.cert.pem

echo "Generate the TLS key config"
echo "See CONFD_DIR/src/confd/yang/tailf-tls.yang for details"
echo "<?xml version=\"1.0\"?>
<config xmlns=\"http://tail-f.com/ns/config/1.0\">
  <tls xmlns=\"http://tail-f.com/ns/tls\">
        <certificate>
          <cert-data>" > ./confd-cdb/tls_data_nopw.xml
cat server.cert.pem >> ./confd-cdb/tls_data_nopw.xml
echo "          </cert-data>
        </certificate>
        <private-key>
          <key-data>" >> ./confd-cdb/tls_data_nopw.xml
cat server.key.pem >> ./confd-cdb/tls_data_nopw.xml
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

echo "Start ConfD"
make start
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -c "wait-start 2"; \
                                    ecode=$?; done;

echo "Start the CDB subscriber example application"
./dhcpd_conf

echo "Quick RESTCONF sanity test using the self-signed CA certificate"
echo "==============================================================="

echo "Generate a client certificate using CA certificate above"
openssl genpkey -algorithm rsa -pkeyopt rsa_keygen_bits:2048 -out client.key.pem
openssl req -new -sha256 -key client.key.pem -subj "/CN=client" -out \
        client.csr.pem
openssl x509 -req -CA root-ca-cert-1.pem  -CAkey root-ca-key-1.pem \
        -CAcreateserial -sha256 -in client.csr.pem -out client.cert.pem

echo "Set some config using RESTCONF YANG-patch in JSON format using curl"
curl -kivu admin:admin -X PATCH --cacert ./root-ca-cert-1.pem --key \
     ./client.key.pem --cert ./client.cert.pem \
     -H "Content-type: application/yang-patch+json" \
     https://localhost:8888/restconf/data -d '
{
  "ietf-yang-patch:yang-patch" : {
    "patch-id" : "dhcpd-patch",
    "edit" : [
      {
        "edit-id" : "edit1",
        "operation" : "merge",
        "target" : "/dhcpd:dhcp",
        "value" : {
          "dhcpd:dhcp": {
            "dhcpd:defaultLeaseTime": "PT42S"
          }
        }
      }
    ]
  }
}'

echo "Get the config over RESTCONF in JSON format using curl"
curl -kivu admin:admin --cacert ./root-ca-cert-1.pem --key ./client.key.pem \
     --cert ./client.cert.pem -H "Accept: application/yang-data+json" \
     https://localhost:8888/restconf/data/dhcpd:dhcp

echo "The resulting ConfD developer log:"
echo "=================================="
tail -n 500 -F devel.log
