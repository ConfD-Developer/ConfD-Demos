FROM debian:10-slim

ARG CONFD_VERSION

ENV CONFD_VERSION=${CONFD_VERSION}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV PATH=${CONFD_DIR}/bin:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd
ENV LD_LIBRARY_PATH=${CONFD_DIR}/lib

WORKDIR /
RUN apt-get update \
    && apt-get install -y --no-install-recommends psmisc libxml2-utils python3 python3-pip python3-setuptools build-essential libssl-dev openssh-client curl htop nano \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir paramiko

COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
RUN ln -s libcrypto.so /usr/lib/x86_64-linux-gnu/libcrypto.so.1.0.0 \
    && /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

# Add the ConfD cryptography integration and C-library API source
ADD confd-${CONFD_VERSION}.libconfd.tar.gz /tmp

# Rebuild the ConfD crypto integration for libcrypto1.1
WORKDIR /tmp/confd-${CONFD_VERSION}/libconfd
RUN make install_crypto

# Cleanup
RUN rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean \
    && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /
ADD app.tar.gz /
WORKDIR /app

# Startup script
CMD [ "./run.sh" ]
