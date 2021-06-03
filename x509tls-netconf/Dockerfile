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
    && apt-get install -y --no-install-recommends gnutls-bin libgnutls28-dev build-essential libssl-dev openssh-client

WORKDIR /tmp
COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
WORKDIR ${CONFD_DIR}
RUN /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

# Rebuild the ConfD crypto integration and cleanup
RUN rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean

ADD ${APP_NAME}.tar.gz /app/

WORKDIR /app
CMD [ "./run.sh" ]
