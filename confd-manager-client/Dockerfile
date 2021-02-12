FROM debian:10-slim

ARG CONFD_VERSION
ARG APP_NAME

ENV CONFD_VERSION=${CONFD_VERSION}
ENV APP_NAME=${APP_NAME}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV USE_SSL_DIR=/usr/lib/x86_64-linux-gnu
ENV LD_LIBRARY_PATH=${USE_SSL_DIR}:$LD_LIBRARY_PATH
ENV PATH=${CONFD_DIR}/bin:${USE_SSL_DIR}/bin:/${APP_NAME}:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd

WORKDIR /
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libssl-dev openssh-client curl libxml2-utils python3 python3-pip python3-setuptools snmp \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir paramiko bs4 lxml pyang

WORKDIR /tmp
COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
WORKDIR ${CONFD_DIR}
RUN ln -s libcrypto.so /usr/lib/x86_64-linux-gnu/libcrypto.so.1.0.0 \
    && /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

# Add the ConfD cryptography integration and C-library API source
ADD confd-${CONFD_VERSION}.libconfd.tar.gz /tmp

# Rebuild the ConfD crypto integration and cleanup
WORKDIR /tmp/confd-${CONFD_VERSION}/libconfd
RUN make USE_SSL_DIR=${USE_SSL_DIR} crypto \
    && make install_crypto \
    && rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean \
    && ln -s /usr/bin/python3 /usr/bin/python

ADD ${APP_NAME}.tar.gz /app/

WORKDIR /app
EXPOSE 4565 2022
CMD [ "./run.sh" ]
