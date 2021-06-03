FROM debian:10-slim

ARG CONFD_VERSION
ARG PKIXSSH_VERSION
ARG APP_NAME
ARG USER=admin
ARG PASS=admin

ENV CONFD_VERSION=${CONFD_VERSION}
ENV APP_NAME=${APP_NAME}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV USE_SSL_DIR=/usr/lib/x86_64-linux-gnu
ENV LD_LIBRARY_PATH=${USE_SSL_DIR}:$LD_LIBRARY_PATH
ENV PATH=${CONFD_DIR}/bin:${USE_SSL_DIR}/bin:/${APP_NAME}:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd
ENV USER=${USER}

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libssl-dev \
       openssh-client ca-certificates wget zlib1g-dev nano isc-dhcp-server sudo

WORKDIR /tmp
RUN echo "sshd:x:74:74:Privilege-separated SSH:/var/empty/sshd:/sbin/nologin" >> /etc/passwd \
    && echo "sshd:x:74:" >> /etc/group \
    && wget https://roumenpetrov.info/secsh/src/pkixssh-${PKIXSSH_VERSION}.tar.gz \
    && tar xvfz pkixssh-${PKIXSSH_VERSION}.tar.gz \
    && cd pkixssh-${PKIXSSH_VERSION} \
    && ./configure \
    && make \
    && make install

COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
RUN  /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

# Rebuild the ConfD crypto integration and cleanup
RUN rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean

# Add user for test purposes
RUN useradd --create-home --home-dir /home/${USER} --user-group --shell /bin/bash ${USER} \
    && echo "${USER}:${PASS}" | chpasswd \
    && chmod -R 755 /home/${USER} \
    && chmod -R 755 /${CONFD_DIR} \
    && chown -R ${USER}:${USER} /home/${USER} \
    && echo "${USER} ALL = (ALL) ALL" >> /etc/sudoers \
    && echo "${USER} ALL = (root) NOPASSWD: /home/${USER}/dhcpd_conf" >> /etc/sudoers \
    && touch /var/lib/dhcp/dhcpd.leases

USER ${USER}
ADD ${APP_NAME}.tar.gz /home/${USER}

# Change priveleges for test purposes
RUN mkdir -p /home/${USER}/.ssh \
    && chmod 700 /home/${USER}/.ssh

WORKDIR /home/${USER}/

CMD [ "./run.sh" ]
