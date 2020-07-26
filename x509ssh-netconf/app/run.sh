#!/bin/bash

echo "Setup NETCONF over PKIX-SSH with x.509v3 authentication"
echo "======================================================="
mkdir -p /home/${USER}/client
mkdir -p /home/${USER}/server

openssl req -nodes -new -x509 -subj "/CN=localhost" -keyout ca.key -out ca.cert
cd client \
    && cp ../ca.cert . \
    && ln -s ca.cert $(openssl x509 -in ca.cert -noout -hash).0 \
    && cd ..
cd server \
    && cp ../ca.cert . \
    && ln -s ca.cert $(openssl x509 -in ca.cert -noout -hash).0 \
    && cd ..
cd client \
    && ssh-keygen -t rsa -b 2048 -f /home/${USER}/.ssh/id_rsa -N "" \
    && openssl req -new -subj "/CN=client" -key /home/${USER}/.ssh/id_rsa -out id_rsa.csr \
    && cp id_rsa.csr ../ \
    && cd ..
openssl x509 -req -CA ca.cert -CAkey ca.key \
        -CAcreateserial \
        -in id_rsa.csr -out id_rsa.cert
cd client \
    && cat ../id_rsa.cert >> /home/${USER}/.ssh/id_rsa \
    && ssh-keygen -y -f /home/${USER}/.ssh/id_rsa > /home/${USER}/.ssh/id_rsa.pub \
    && echo "x509v3-sign-rsa $(openssl x509 -noout -subject -in /home/${USER}/.ssh/id_rsa)" > ../server/authorized_keys \
    && chmod 600 ../server/authorized_keys \
    && cd ..
cd server \
    && openssl req -new -subj "/CN=localhost.tail-f.com" -key ${CONFD_DIR}/etc/confd/ssh/ssh_host_rsa_key -out ssh_host_rsa_key.csr \
    && cd ..
cp server/ssh_host_rsa_key.csr . \
    && openssl x509 -req -in ssh_host_rsa_key.csr -out ssh_host_rsa_key.cert -CA ca.cert -CAkey ca.key
cd server \
    && cp ../ssh_host_rsa_key.cert . \
    && cp ${CONFD_DIR}/etc/confd/ssh/ssh_host_rsa_key* . \
    && chmod 600 ssh_host_rsa_key && chmod 600 ssh_host_rsa_key.pub \
    && cat ssh_host_rsa_key.cert >> ssh_host_rsa_key \
    && ssh-keygen -y -f ssh_host_rsa_key > ssh_host_rsa_key.pub \
    && echo "AuthorizedKeysFile  /home/${USER}/server/authorized_keys" > sshd_config \
    && echo "KeyAllowSelfIssued yes" >> sshd_config \
    && echo "CACertificatePath /home/${USER}/server" >> sshd_config \
    && echo "PasswordAuthentication no" >> sshd_config \
    && echo "HostKey /home/${USER}/server/ssh_host_rsa_key" >> sshd_config \
    && echo "UsePrivilegeSeparation sandbox" >> sshd_config \
    && echo "Subsystem       netconf    /home/${USER}/netconf-subsys" >> sshd_config \
    && /usr/local/sbin/sshd -p 2022 -f ./sshd_config \
    && cd ..
cd client \
    && echo "StrictHostKeyChecking no" > ssh_config \
    && echo "CACertificatePath /home/${USER}/client" >> ssh_config \
    && echo "UserCACertificatePath /home/${USER}/client" >> ssh_config \
    && echo "PasswordAuthentication no" >> ssh_config \
    && ssh -vv -p 2022 -F ssh_config localhost find . -type f \
    && cd ..

echo "Compile YANG and Build the PKIX-SSH OpenSSH subsystem and subscriber example applications"
ln -s ${CONFD_DIR}/src/confd/netconf/netconf-subsys.c netconf-subsys.c
mkdir -p confd-cdb
cp nacm_init.xml confd-cdb/
make all start
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -c "wait-start 2"; ecode=$?; done;

echo "Start the CDB subscriber example application"
sudo ./dhcpd_conf

cd client \
    && ssh -s -p 2022 -F ssh_config localhost netconf <<< $(cat ../cmd-set-dhcp-subnet.xml) \
    && ssh -s -p 2022 -F ssh_config localhost netconf <<< $(cat ../cmd-set-dhcp-defaultLeaseTime-1h.xml) \
    && ssh -s -p 2022 -F ssh_config localhost netconf <<< $(cat ../cmd-get-dhcpd.xml) \
    && ssh -s -p 2022 -F ssh_config localhost netconf <<< $(cat ../cmd-del-dhcp-defaultLeaseTime.xml) \
    && cd ..

echo "The NETCONF communication is logged in the netconf.trace file"
echo "============================================================="
cat netconf.trace

echo "The resulting ConfD developer log:"
echo "=================================="
tail -n 500 -F devel.log
