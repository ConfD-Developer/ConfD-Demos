FROM debian:10-slim

ARG NSO_VERSION
ARG APP_NAME

ENV NSO_VERSION=${NSO_VERSION}
ENV APP_NAME=${APP_NAME}

ENV DEBIAN_FRONTEND=noninteractive
ENV NCS_DIR=/nso
ENV LD_LIBRARY_PATH=/nso/lib
ENV PYTHONPATH=/nso/src/ncs/pyapi
ENV PATH=/nso/bin:$PATH

COPY nso-${NSO_VERSION}.linux.x86_64.signed.bin /tmp
WORKDIR /tmp

RUN mkdir -p /usr/share/man/man1 \
    && apt-get update \
    && apt-get install -y --no-install-recommends ant libxml2-utils xsltproc \
       default-jre python3-pip python3-setuptools build-essential libssl-dev \
       openssh-client libfontconfig1 git iproute2 iputils-ping nano \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && chmod +x /tmp/nso-${NSO_VERSION}.linux.x86_64.signed.bin \
    && /tmp/nso-${NSO_VERSION}.linux.x86_64.signed.bin --skip-verification \
    && chmod +x /tmp/nso-${NSO_VERSION}.linux.x86_64.installer.bin \
    && /tmp/nso-${NSO_VERSION}.linux.x86_64.installer.bin ${NCS_DIR} \
    && rm -rf ${NCS_DIR}/examples.ncs ${NCS_DIR}/doc

ADD ${APP_NAME}-nso.tar.gz /${APP_NAME}_nso

WORKDIR /${APP_NAME}_nso/packages
RUN git clone https://github.com/NSO-developer/drned-xmnr \
    && python -m pip install --upgrade pip \
    && python -m pip install -r drned-xmnr/requirements.txt \
    && python -m pip install --no-cache-dir paramiko

RUN apt-get autoremove -y \
    && apt-get clean

WORKDIR /${APP_NAME}_nso
# Startup script
EXPOSE 18080
CMD [ "./run.sh" ]
