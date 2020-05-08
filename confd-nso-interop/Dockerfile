FROM debian:10-slim

ARG CONFD_VERSION
ARG NSO_VERSION
ARG APP_NAME

ENV CONFD_VERSION=${CONFD_VERSION}
ENV NSO_VERSION=${NSO_VERSION}
ENV APP_NAME=${APP_NAME}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV NCS_DIR=/nso
ENV LD_LIBRARY_PATH=/nso/lib:/confd/lib PYTHONPATH=/nso/src/ncs/pyapi
ENV PATH=/confd/bin:/nso/bin:$PATH

COPY nso-${NSO_VERSION}.linux.x86_64.signed.bin /tmp
WORKDIR /tmp

RUN mkdir -p /usr/share/man/man1 \
    && apt-get update \
    && apt-get install -y --no-install-recommends ant libxml2-utils xsltproc \
       default-jre python3-pip python3-setuptools build-essential libssl-dev \
       openssh-client libfontconfig1 git \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir paramiko lxml pexpect pytest \
    && /tmp/nso-${NSO_VERSION}.linux.x86_64.signed.bin --skip-verification \
    && chmod +x /tmp/nso-${NSO_VERSION}.linux.x86_64.installer.bin \
    && /tmp/nso-${NSO_VERSION}.linux.x86_64.installer.bin ${NCS_DIR} \
    && rm -rf ${NCS_DIR}/examples.ncs ${NCS_DIR}/doc

COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
WORKDIR ${CONFD_DIR}
RUN ln -s libcrypto.so /usr/lib/x86_64-linux-gnu/libcrypto.so.1.0.0 \
    && /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR} \
    && rm -rf examples.confd doc

# Add the ConfD cryptography integration and C-library API source
ADD confd-${CONFD_VERSION}.libconfd.tar.gz /tmp

# Rebuild the CondfD crypto integration for libcrypto1.1
WORKDIR /tmp/confd-${CONFD_VERSION}/libconfd
RUN make install_crypto \
    && apt-get autoremove -y \
    && apt-get clean

ADD ${APP_NAME}-confd.tar.gz /${APP_NAME}_confd
ADD ${APP_NAME}-nso.tar.gz /${APP_NAME}_nso

WORKDIR /${APP_NAME}_nso/packages
RUN git clone https://github.com/NSO-developer/drned-xmnr

# Flatten any directory with YANG models if necessary
WORKDIR /${APP_NAME}_confd/yang
find . -name "*.yang" -exec cp {} . \; \

EXPOSE 18080
WORKDIR /${APP_NAME}_nso

CMD [ "./run.sh" ]
