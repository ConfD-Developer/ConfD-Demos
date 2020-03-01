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

/* For debug purposes */
static void print_value_array(confd_value_t vs[], int n)
{
    char tmpbuf[BUFSIZ];
    int i;

    for (i=0; i<n; i++) {
      confd_pp_value(tmpbuf, BUFSIZ, &vs[i]);
      printf("%s ", tmpbuf);
    }
}

/* Begin demo code */
int main(int argc, char *argv[])
{
  struct sockaddr_in addr;
  struct maapi_cursor mc;
  int c, i, thandle, maapisock, values_per_entry, ret;
  int nobj;
  confd_value_t *v, inkeys[1];
  struct confd_cs_node *object;
  struct confd_ip ip;
  const char *user = "admin", *groups[] = { "admin" }, *context = "system";
  char *inkey = NULL;
  char *path = "/r:sys/routes/inet/route";
  char *confd_ip = "127.0.0.1";
  int confd_port = CONFD_PORT;
  int debuglevel = CONFD_DEBUG, entries_per_request = 100;

  while ((c = getopt(argc, argv, "a:p:u:g:c:P:k:e:drts")) != EOF) {
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
    case 'p':
      path = optarg;
      break;
    case 'k':
      inkey = optarg;
      break;
    case 'e':
      entries_per_request = atoi(optarg);
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

  object = confd_cs_node_cd(NULL, path);
  values_per_entry = confd_max_object_size(object);

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
    confd_fatal("Failed to start trans\n");
  }

  if(maapi_init_cursor(maapisock, thandle, &mc, path) != CONFD_OK)
    confd_fatal("maapi_init_cursor() failed\n");

  if(inkey != NULL) {
    CONFD_SET_STR(&inkeys[0], &inkey[0]);
    if (maapi_find_next(&mc, CONFD_FIND_SAME_OR_NEXT, inkeys, 1) != CONFD_OK)
      confd_fatal("maapi_find_next() failed\n");
    if(mc.n == 0) {
      fprintf(stderr, "Key \"%s\" not found\n", inkey);
      exit(0);
    }
  }

  v = malloc(sizeof(confd_value_t) * values_per_entry * entries_per_request);
  do {
    nobj = entries_per_request;
    ret = maapi_get_objects(&mc, v, values_per_entry, &nobj);
    if (ret >= 0) {
      for (i = 0; i < nobj; i++) {
        printf("%d: ", i);
        print_value_array(&v[i*values_per_entry], values_per_entry);
        printf("\n");
      }
    } else {
      confd_fatal("maapi_get_objects() failed\n");
    }
  } while (ret >= 0 && mc.n != 0);
  free(v);
  maapi_destroy_cursor(&mc);
}
