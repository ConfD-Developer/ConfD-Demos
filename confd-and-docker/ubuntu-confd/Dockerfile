# ConfD Daemon Container Image

# Start from the Ubuntu 18:04 Linux base image.
FROM ubuntu:18.04
LABEL description="Docker image that demonstrates how to run ConfD inside a Docker container."
LABEL maintainer="jojohans@cisco.com"

# The environment needed by ConfD
ENV CONFD_DIR=/confd LD_LIBRARY_PATH=/confd/lib PATH=/confd/bin:$PATH

# Install extra packages needed to run ConfD.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libssl1.0-dev \
        openssh-client && mkdir -p ${CONFD_DIR}
RUN ln -sv /usr/lib/x86_64-linux-gnu/libcrypto.so.1.0.2 /usr/lib/x86_64-linux-gnu/libcrypto.so.1.0.0

### Cleanup the image.
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# We will run ConfD as a non-root user.
RUN addgroup confd
RUN useradd confd -g confd
RUN mkdir -p ${CONFD_DIR} && chown confd:confd /confd

# For some reason COPY --chown=confd:confd /tmp/confd-target.tgz
# doesn't work with the debian base image.  It work fine with Ubuntu
# and Alpine Linux, ... not sure what's going on.
COPY resources/confd-target.tgz /tmp/confd-target.tgz
RUN chown -v confd:confd /tmp/confd-target.tgz
USER confd

# Install ConfD in the container.  Note that this isn't a regular ConfD "installler"
# installation, instead we only include the files required for a minimal
# target installation as described in section 31.3. Installing ConfD on a
# target system in the ConfD User Guide.
COPY resources/confd-target.tgz /tmp
RUN tar xzf /tmp/confd-target.tgz -C ${CONFD_DIR} #&& rm /tmp/confd-target.tgz
RUN yes | ssh-keygen -f /confd/etc/confd/ssh/ssh_host_rsa_key -N "" -t rsa -m pem

# Add volumes and the working directory.
WORKDIR /confd

# Expose ports for required northbound protocols as necessary.
EXPOSE 2022 2024 4565
# NETCONF over TCP, HA replication and HTTP(S) are not used in this example.
#EXPOSE 2023 4569 8008 8088

# Start ConfD.
CMD ["/confd/bin/confd", "--foreground"]
