# A target installation og ConfD with external SSH server container image

## Summary

This docker image use a two-stage build to create a minimal ConfD
target installation configured to use openssh for terminating NETCONF
and CLI connections. Additionally the container image supports PAM authentication
through RADIUS or LDAP.

The files needed for a target installation is described in section
`32.2 Installing ConfD on a target system` from the `ConfD User Guide`.

## Prerequisites

 o A ConfD Linux installer located in a sub directory named
   `resources/confd/<confd version>`.  Examples and documentation
   tar-balls are not needed since they aren't used in the target
   installation.  Note that the Dockerfile assumes a signed installer,
   i.e. ConfD 7.6 or newer.

## Steps


1. In the first stage we create the image for the specified ConfD
   version (Currently the container defaults to `ConfD 7.8`, the
   latest major version at time of writing).  Pass the flag
   `--build-arg ver=<confd version>` to build for a different ConfD
   version.

2. In the second stage of the build we only add OS-packages used in
   run time, add the target package created in step 1 and other setup
   required.

3. Run the docker image and expose the NETCONF, CLI and internal IPC
   ports. Note that NETCONF and CLI ports are exposed by sshd, only
   the IPC port goes to ConfD.

    `$ docker run -it --rm -p 2022:2022 -p 2024:2024 -p 4565:4565 \
                     --hostname ssh-confd --name ssh-confd --init \
                     ssh-confd:v7.8`
