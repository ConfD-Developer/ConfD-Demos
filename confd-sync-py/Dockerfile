FROM debian:11-slim

ARG CONFD_VERSION

ENV CONFD_VERSION=${CONFD_VERSION}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV PATH=${CONFD_DIR}/bin:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd
ENV LD_LIBRARY_PATH=${CONFD_DIR}/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=$CONFD_DIR/src/confd/pyapi:$PYTHONPATH

WORKDIR /
RUN apt-get update \
    && apt-get install -y --no-install-recommends psmisc libxml2-utils python3 \
    python3-pip python3-setuptools build-essential libssl-dev openssh-client \
    htop nano \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir paramiko

COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
RUN /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

# Cleanup
RUN rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean \
    && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /
ADD app.tar.gz /
WORKDIR /app

# Start one of the ConfD Python examples
EXPOSE 4565 2022
CMD [ "./run.sh" ]
