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

static enum maapi_iter_ret iter(confd_hkeypath_t *kp,
                                confd_value_t *v,
                                confd_attr_value_t *attr_vals,
                                int num_attr_vals,
                                void *state)
{
  char path[BUFSIZ];
  char value[BUFSIZ];
  char *rnode = "/r:sys";
  int rlen = strlen(rnode);
  struct confd_cs_node *cs_node;

  strcpy(&path[0],rnode);
  kp->len = kp->len-1;
  confd_pp_kpath(&path[rlen], BUFSIZ, kp);

  if (v != NULL) {
    value[0] = 0;
    cs_node = confd_cs_node_cd(NULL, path);
    if (cs_node == NULL) {
      confd_pp_value(&value[0], BUFSIZ, v);
    } else {
      confd_val2str(cs_node->info.type, v, &value[0], BUFSIZ);
    }
    printf("%s %s\n", path, value);
  }
  return ITER_RECURSE;
}

/* Begin demo code */
int main(int argc, char *argv[])
{
  struct sockaddr_in addr;
  int c, thandle, maapisock, ret;
  struct confd_ip ip;
  const char *user = "admin", *groups[] = { "admin" }, *context = "system";
  char *path = "/r:sys";
  char *confd_ip = "127.0.0.1";
  int confd_port = CONFD_PORT;
  int debuglevel = CONFD_DEBUG;
  int datastore = CONFD_RUNNING;

  while ((c = getopt(argc, argv, "a:P:u:g:c:p:CROdrts")) != EOF) {
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
    case 'C':
      datastore = CONFD_CANDIDATE;
      break;
    case 'R':
      datastore = CONFD_RUNNING;
      break;
    case 'O':
      datastore = CONFD_OPERATIONAL;
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
  confd_init("maapi-iterate", stderr, debuglevel);

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

  if ((thandle = maapi_start_trans(maapisock,datastore,
                                   CONFD_READ)) < 0) {
    confd_fatal("Failed to start trans");
  }
  ret = maapi_iterate(maapisock, thandle, iter, 0, NULL, path);
  if (ret != CONFD_OK)
    confd_fatal("maapi_iterate() failed");
  maapi_close(maapisock);
}
