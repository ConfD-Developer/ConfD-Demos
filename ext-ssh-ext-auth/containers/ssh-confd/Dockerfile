# ConfD Daemon Container Image

# Start from the latest Ubuntu LTS linux base image.
FROM ubuntu:20.04
LABEL description="Docker image for ConfD with external SSH server."
LABEL maintainer="jojohans@cisco.com"

# The environment needed by ConfD
ENV CONFD_DIR=/confd LD_LIBRARY_PATH=/confd/lib PATH=/confd/bin:$PATH

# Install extra packages needed to install ConfD and create the target
# installation package.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    openssh-client \
    openssl \
    python-is-python3 \
    && mkdir -p $CONFD_DIR

# Cleanup the image.
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ARG ver=7.8

# Install the full ConfD SDK in the container (no need for documentation or
# examples).  We expect to find the installer in the resources/confd/<ver>
# directory. Automatically build netconf-subsys since we need it for
# ssh-server integration.
COPY --chown=confd:confd resources/confd/${ver}/* /tmp/
RUN cd /tmp && \
    /tmp/confd-${ver}.linux.x86_64.signed.bin && \
    /tmp/confd-${ver}.linux.x86_64.installer.bin --skip-docs --skip-examples ${CONFD_DIR} && \
    tar xzf /tmp/confd-${ver}.libconfd.tar.gz --strip-components 1 -C ${CONFD_DIR} && \
    make -C ${CONFD_DIR}/src/confd/netconf USE_IPC=yes all && \
    cp ${CONFD_DIR}/src/confd/netconf/netconf-subsys ${CONFD_DIR}/bin

# The builder scripts creates a tar-ball with the files required for a
# ConfD target installation. We'll use the tar-ball when creating the final
# image.
COPY --chown=confd:confd resources/scripts/builder /tmp/builder
RUN /tmp/builder

################################################################################
################################################################################

# Start from the latest Ubuntu LTS linux base image.
FROM ubuntu:20.04
LABEL description="Docker image for ConfD with external SSH server."
LABEL maintainer="jojohans@cisco.com"

# The environment needed by ConfD.
ENV CONFD_DIR=/confd LD_LIBRARY_PATH=/confd/lib PATH=/confd/bin:$PATH

# Install ubuntu packages we need.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ldap-utils \
    libpam-radius-auth \
    libssl-dev \
    netbase \
    openssh-server \
    python3-paramiko \
    supervisor \
    syslog-ng \
    libxml2-utils \
    && mkdir -p $CONFD_DIR \
    && mkdir -p /supervisord/log \
    && mkdir -p /supervisord/run \
    && mkdir -p /run/sshd

### Debug packages, not needed if everything is working.
##RUN apt-get install -y --no-install-recommends \
##    iproute2 \
##    iputils-ping \
##    pamtester \
##    strace \
##    tcpdump

# Add ConfD users
RUN adduser admin --disabled-password --quiet --gecos "" && \
    adduser oper --disabled-password --quiet --gecos ""

# We have to add Match statement in the main sshd_config file rather than
# in the include file due to a bug in OpenSSH 8.2 (default in Ubuntu 20.04).
# Currently we can't run on Ubuntu 22.04, which doesn't suffer from the
# aforementioned bug, because ConfD 7.8 doesn't support openssl3 which is
# the only version available in Ubuntu 22.04.
RUN echo "Match LocalPort 2024\n    ForceCommand /confd/bin/confd_cli" >> /etc/ssh/sshd_config

# We will run ConfD as a non-root user.
RUN useradd confd
RUN mkdir -p $CONFD_DIR && chown confd:confd /confd

# Install ConfD in the container.
COPY --chown=confd:confd --from=0 /tmp/confd-target.tgz /tmp
USER confd
RUN tar xzf /tmp/confd-target.tgz -C $CONFD_DIR && rm /tmp/confd-target.tgz

# Create internal "state" directories referenced by the default
# confd.conf from the package above.
RUN mkdir -p \
        ${CONFD_DIR}/var/confd/candidate \
        ${CONFD_DIR}/var/confd/cdb \
        ${CONFD_DIR}/var/confd/log \
        ${CONFD_DIR}/var/confd/rollback \
        ${CONFD_DIR}/var/confd/state \
        ${CONFD_DIR}/var/confd/webui

# Add volumes and the working directory.
WORKDIR /supervisord

# Expose ports for required northbound protocols as necessary.
EXPOSE 2022 2024 4565

# NETCONF over TCP, HA replication and HTTP(S) are not used in this example.
#EXPOSE 2023 4569 8008 8088

# Switch back to root
USER root

# Cleanup the image.
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Start supervisord
ENTRYPOINT ["/usr/bin/supervisord"]
