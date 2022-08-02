# ConfD Demo with External SSH Server and Externa Authentication

## Introduction

ext-ssh-ext-auth is a multi container application demonstrating how to
run confd with an external ssh server while at the same time using
external authentication. The application consist of two containers,
one including confd and an ssh server, the other an external
authentication service. docker-compose is used to manage the
application, the containers and the configuration files.

To the largest extent possible the containers are generic with all
configuration provided from the outside when docker-compose launch the
containers.

The sshd container expose ports 2022 (NETCONF) and 2024 (CLI) to the host.

The demo assumes that docker and docker compose is already installed
and that ConfD or ConfD Basic is available.

## Running the Demo

 o Clone the ext-auth-ext-ssh demo to a local directory

   `git clone https://github.com/ConfD-Developer/ConfD-Demos/tree/master/ext-auth-ext-ssh`

 o Copy the ConfD installer to ./resources/confd/<confd-version>

   `cp /path/to/confd/<confd version>/confd-<confd-version>.linux.x86_64.signed.bin ./resources/confd/<confd-version>`

 o Build the demo using the docker compose build command.  Note that
   the demo assumes ConfD (Basic) version 7.8.2.  If you use a different
   ConfD version, you must provide the correct version using --build-arg.

   `docker compose build --build-arg confd-ver=<confd-version>`

 o Start the demo
 `docker compose up --detach`

 o Run the following commands to verify that you can access NETCONF and CLI on ConfD

   `ssh -p 2024 admin@localhost`

   `ssh -p 2022 -s oper@localhost netconf`

   If ConfD is installed on the host you can obviously also use netconf-console directly

   `netconf-console --hello`

 o You see what's going on by viewing the container logs.

   If anything goes wrong, logging from ConfD and ssh is available on
   respective container consoles

   `docker compose logs ssh-confd`

   `docker compose logs radius`
