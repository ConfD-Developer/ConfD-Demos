/*
 * Copyright 2019 Tail-F Systems AB
 */

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/poll.h>

#include <confd_lib.h>
#include <confd_maapi.h>

/* Begin demo code */
int main(int argc, char *argv[])
{
  struct sockaddr_in addr;
  int c, thandle, maapisock, id, ssock, r;
  int flags = (MAAPI_CONFIG_XML|MAAPI_CONFIG_OPER_ONLY);
  struct confd_ip ip;
  const char *user = "admin", *groups[] = { "admin" }, *context = "system";
  char *path = "/r:sys";
  char *confd_ip = "127.0.0.1";
  int confd_port = CONFD_PORT;
  int debuglevel = CONFD_DEBUG;
  char buf[BUFSIZ];

  while ((c = getopt(argc, argv, "a:p:u:g:c:jxh:drts")) != EOF) {
    switch(c) {
    case 'a':
      confd_ip = optarg;
      break;
    case 'P':
      confd_port = atoi(optarg);
      break;
    case 'u':
      user = optarg;
      break;
    case 'g':
      groups[0] = optarg;
      break;
    case 'c':
      context = optarg;
      break;
    case 'j':
      flags = (MAAPI_CONFIG_JSON|MAAPI_CONFIG_OPER_ONLY);
      break;
    case 'x':
      flags = (MAAPI_CONFIG_XML_PRETTY|MAAPI_CONFIG_OPER_ONLY);
      break;
    case 'p':
      path = optarg;
      break;
    case 'd':
      debuglevel = CONFD_DEBUG;
      break;
    case 'r':
      debuglevel = CONFD_PROTO_TRACE;
      break;
    case 't':
      debuglevel = CONFD_TRACE;
      break;
    case 's':
      debuglevel = CONFD_SILENT;
      break;
    }
  }

  confd_init("maapi-get-objs", stderr, debuglevel);

  addr.sin_addr.s_addr = inet_addr(confd_ip);
  addr.sin_family = AF_INET;
  addr.sin_port = htons(confd_port);

  if (confd_load_schemas((struct sockaddr*)&addr,
                         sizeof (struct sockaddr_in)) != CONFD_OK)
    confd_fatal("Failed to load schemas from ConfD\n");

  if ((maapisock = socket(PF_INET, SOCK_STREAM, 0)) < 0)
    confd_fatal("Failed to create the MAAPI socket");
  if (maapi_connect(maapisock, (struct sockaddr*)&addr,
                    sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to confd_connect() to ConfD\n");

  ip.af = AF_INET;
  inet_pton(AF_INET, confd_ip, &ip.ip.v4);

  if ((maapi_start_user_session(maapisock, user, context, groups,
                                sizeof(groups) / sizeof(*groups),
                                &ip,
                                CONFD_PROTO_TCP) != CONFD_OK)) {
    confd_fatal("Failed to start user session");
  }

  if ((thandle = maapi_start_trans(maapisock,CONFD_OPERATIONAL,
                                   CONFD_READ)) < 0) {
    confd_fatal("Failed to start trans");
  }

  id = maapi_save_config(maapisock, thandle, flags, path);
  if (id < 0)
    confd_fatal("maapi_save_config() failed to start");

  ssock = socket(PF_INET, SOCK_STREAM, 0);
  confd_stream_connect(ssock, (struct sockaddr*)&addr, sizeof(struct sockaddr_in), id, 0);
  while ((r = read(ssock, buf, sizeof(buf))) > 0) {
    if (fwrite(buf, 1, r, stdout) != r)
      confd_fatal("Failed to write output");
  }
  if (r < 0)
    confd_fatal("Failed to read from stream socket");
  close(ssock);
  if (maapi_save_config_result(maapisock, id) != CONFD_OK)
    confd_fatal("maapi_save_config() failed");
  printf("\n");
  maapi_close(maapisock);
}
