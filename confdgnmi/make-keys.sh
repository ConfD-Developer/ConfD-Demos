openssl req -x509 -newkey rsa:4096 -sha256 -nodes -keyout server.key -subj "/CN=localhost/C=US/ST=CA/L=SanJose/O=Cisco/CN=www.cisco.com" -out server.crt
openssl req -x509 -newkey rsa:4096 -sha256 -nodes -keyout client.key -subj "/CN=localhost/C=US/ST=CA/L=SanJose/O=Cisco/CN=www.cisco.com" -out client.crt
