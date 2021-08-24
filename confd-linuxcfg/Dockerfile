FROM debian:11

ARG CONFD_VERSION

ENV CONFD_VERSION=${CONFD_VERSION}
ENV CONFD_DIR=/confd
ENV DEBIAN_FRONTEND=noninteractive
ENV USE_SSL_DIR=/usr/lib/x86_64-linux-gnu
ENV LD_LIBRARY_PATH=${USE_SSL_DIR}:${CONFD_DIR}/lib:$LD_LIBRARY_PATH
ENV PATH=${CONFD_DIR}/bin:${USE_SSL_DIR}/bin:/home/${USER}:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd

WORKDIR /
RUN apt-get update \
    && apt-get install -y --no-install-recommends libssl-dev openssh-client \
       build-essential python3 python3-pip python3-setuptools nano \
       libxml2-utils procps ethtool iproute2 sudo \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir paramiko

COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
COPY confd-${CONFD_VERSION}.examples.tar.gz /tmp
RUN /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

COPY run.sh ${CONFD_DIR}/examples.confd/linuxcfg/

# Cleanup
RUN rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean \
    && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR ${CONFD_DIR}/examples.confd/linuxcfg
EXPOSE 2022 2024
CMD [ "./run.sh" ]
