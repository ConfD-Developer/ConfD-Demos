# Build ConfD target package

# Start from alpine linux base image.  The base image we use doesn't
# matter for this container, we just install ConfD and run the builder
# script.
FROM alpine:3.10.2
LABEL description="Docker image to generate the ConfD target installation package."
LABEL maintainer="jojohans@cisco.com"

ENV CONFD_DIR=/confd

# Default to latest version of ConfD.  Override on the command line
# with --build-arg ver=<version>.
ARG ver=7.2.0.1

# Install extra packages needed to install ConfD.
RUN apk --no-cache add openssh-keygen

# We will run ConfD as a non-root user.
RUN addgroup confd && adduser -D -G confd confd
RUN mkdir -p ${CONFD_DIR} && chown confd:confd ${CONFD_DIR}
USER confd

# Install ConfD in the container (no need for documentation or
# examples).  We expect to find the installer in a directory called
# confd/confd-<ver>.
COPY resources/confd/$ver/* /tmp/
RUN sh -c "/tmp/confd-$ver.linux.x86_64.installer.bin --skip-docs --skip-examples ${CONFD_DIR} &> /dev/null"

# Add the build script.
ADD resources/* /

# Run the build script.
ENTRYPOINT ["/builder"]
