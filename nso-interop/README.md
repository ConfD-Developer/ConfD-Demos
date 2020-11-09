An NSO interop testing image
============================

Build a NSO interop testing container image, including a NETCONF NED
for the device and the test-tool drned-xmnr..

Prerequisites
-------------

NSO-installer, e.g. from https://developer.cisco.com/site/nso/
YANG-models for the device you want to test.

Steps
-----
1. Drop the NSO installer image into the resources directory.
2. Drop the device YANG-models into the resources/yangs directory.
3. Create the NSO Interop testing image

`$ docker build --tag nso-interop:<version> .`

   The Dockerfile has a number of ARGs that lets you override things
   line NSO-version target IP-address and port etc, the defaults can
   be changed by passing one or more `--build-arg='parameter=value'` to
   the `docker build` command.  See the Dockerfile for details.

4. Run the docker image and expose the NETCONF and internal IPC ports.

`$ docker run -it --rm -p 2024:2024 -p 4569:4569 --init --hostname nso-interop --name nso-interop nso-interop:<version>`

   In order to help troubleshooting it makes sense to mount logs and
   DrNED Examiner directories from outside of the container:

`$ docker run -d --rm -p 2024:2024 -p 4569:4569 \
              --mount type=bind,source=$(pwd)/interop-logs,target=/interop/logs \
              --mount type=bind,source=$(pwd)/interop-xmnr,target=/interop/xmnr \
              --mount type=bind,source=$(pwd)/interop-states,target=/interop/states \
              --mount type=bind,source=$(pwd)/interop-yangs,target=/interop/yangs \
              --init --hostname nso-interop --name nso-interop nso-interop:<version>`

   Assuming the interop-logs and interop-xmnr volumes already exist in
   current working directory.

4. Start the NSO CLI and use drned-xmnr as described in the README at `https://github.com/NSO-developer/drned-xmnr.git`.

5. The container includes a script that make it easy to rebuild the
   existing NED or build a new one.  Add the YANG-models you want to
   include in the NED to the interop-yangs directory and run the
   following command: `docker exec nso-interop build-ned <ned-name> <vendor> <version>`.
