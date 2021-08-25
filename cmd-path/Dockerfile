FROM debian:11-slim

ARG CONFD_VERSION

ENV CONFD_VERSION=${CONFD_VERSION}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV PATH=${CONFD_DIR}/bin:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd
ENV LD_LIBRARY_PATH=${CONFD_DIR}/lib

WORKDIR /
RUN apt-get update \
    && apt-get install -y --no-install-recommends psmisc libxml2-utils python3 python3-pip python3-setuptools python3-dev build-essential libssl-dev openssh-client curl htop nano \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir paramiko bs4 lxml pyang

COPY confd-${CONFD_VERSION}.linux.x86_64.installer.bin /tmp
RUN /tmp/confd-${CONFD_VERSION}.linux.x86_64.installer.bin ${CONFD_DIR}

# Add the ConfD cryptography integration and C-library API source
ADD confd-${CONFD_VERSION}.libconfd.tar.gz /tmp

# Rebuild libconfd
WORKDIR /tmp/confd-${CONFD_VERSION}/libconfd
RUN make EXTRA_CFLAGS="-DMAXDEPTH=30 -DMAXKEYLEN=12" && make install

# Rebuild the ConfD Python API
WORKDIR ${CONFD_DIR}/src/confd/pyapi
RUN make CFLAGS="-DMAXDEPTH=30 -DMAXKEYLEN=12 -g -fstack-protector-strong -Wformat -Werror=format-security" clean confd-py3

# Cleanup
RUN rm -rf /tmp/* /var/tmp/* \
    && apt-get autoremove -y \
    && apt-get clean

ADD app.tar.gz /
WORKDIR /app

# Startup script
CMD [ "./run.sh" ]
