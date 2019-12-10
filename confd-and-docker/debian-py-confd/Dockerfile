FROM python:3

ARG CONFD_VERSION

ENV CONFD_VERSION=${CONFD_VERSION}
ENV DEBIAN_FRONTEND=noninteractive
ENV CONFD_DIR=/confd
ENV PATH=${CONFD_DIR}/bin:$PATH
ENV CONFD=${CONFD_DIR}/bin/confd
ENV LD_LIBRARY_PATH=${CONFD_DIR}/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=$CONFD_DIR/src/confd/pyapi:$PYTHONPATH

WORKDIR /
RUN pip install --upgrade pip \
    && pip install --no-cache-dir paramiko \
    && apt-get update \
    && apt-get install psmisc libxml2-utils

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
    && apt-get clean

WORKDIR /
# Startup script for the ConfD cdb.get_modifications() Python example
ADD app.tar.gz /
WORKDIR /app

# Start one of the ConfD Python examples
EXPOSE 4565 2022
CMD [ "./run.sh" ]
