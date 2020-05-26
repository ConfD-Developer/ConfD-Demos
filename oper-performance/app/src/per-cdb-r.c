#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/poll.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>

#include <confd_lib.h>
#include <confd_cdb.h>

/* The header file generated from the YANG module */
#include "routes.h"

#define SUBPATH "/r:routes"

/* Tag value print helper function */
#if 0
static void print_tag_value_array(confd_tag_value_t *val, int nvals,
                                  struct confd_cs_node *start_node,
                                  int start_indent)
{
  int i, indent = start_indent;
  struct confd_cs_node root, *pnode = start_node, *node;
  char tmpbuf[BUFSIZ];
  char *tmp;

  for (i=0; i<nvals; i++) {
    if (indent == start_indent && start_node == NULL) {
      node = confd_find_cs_root(CONFD_GET_TAG_NS(&val[i]));
      root.children = node;
      pnode = &root;
    }
    switch (CONFD_GET_TAG_VALUE(&val[i])->type) {
    case C_XMLBEGIN:
      tmp = "begin";
      if (pnode != NULL)
        pnode = confd_find_cs_node_child(pnode, val[i].tag);
      break;
    case C_XMLBEGINDEL:
      tmp = "begin-deleted";
      if (pnode != NULL)
        pnode = confd_find_cs_node_child(pnode, val[i].tag);
      break;
    case C_XMLEND:
      tmp = "end";
      if (pnode != NULL)
        pnode = pnode->parent;
      indent -= 2;
      break;
    case C_XMLTAG:
      tmp = "created";
      break;
    case C_NOEXISTS:
      tmp = "deleted";
      break;
    default:
      if (pnode == NULL ||
          (node = confd_find_cs_node_child(pnode, val[i].tag)) == NULL ||
          confd_val2str(node->info.type, CONFD_GET_TAG_VALUE(&val[i]),
                        tmpbuf, sizeof(tmpbuf)) == CONFD_ERR) {
        confd_pp_value(tmpbuf, sizeof(tmpbuf),
                       CONFD_GET_TAG_VALUE(&val[i]));
      }
      tmp = tmpbuf;
    }
    fprintf(stderr, "%*s%s %s\n", indent, "",
           confd_hash2str(CONFD_GET_TAG_TAG(&val[i])), tmp);
    switch (CONFD_GET_TAG_VALUE(&val[i])->type) {
    case C_XMLBEGIN:
    case C_XMLBEGINDEL:
      indent += 2;
      break;
    default:
      break;
    }
  }
}
#endif

static int runtest(char *confd_addr, int confd_port) {
  struct sockaddr_in addr;
  int subsock, subpoint, status, nvals;

  addr.sin_addr.s_addr = inet_addr(confd_addr);
  addr.sin_family = AF_INET;
  addr.sin_port = htons(confd_port);

  if (confd_load_schemas((struct sockaddr*)&addr, sizeof (struct sockaddr_in)) != CONFD_OK)
    confd_fatal("Failed to load schemas from confd\n");

  if ((subsock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open socket\n");

  if (cdb_connect(subsock, CDB_SUBSCRIPTION_SOCKET, (struct sockaddr*)&addr, sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to cdb_connect() to confd \n");

  /* setup subscription point */

  if ((status = cdb_oper_subscribe(subsock, r__ns, &subpoint, SUBPATH)) != CONFD_OK) {
    confd_fatal("Terminate: subscribe %d\n", status);
  }
  if (cdb_subscribe_done(subsock) != CONFD_OK)
    confd_fatal("cdb_subscribe_done() failed");

  while (1) {
    int status;
    struct pollfd set[1];

    set[0].fd = subsock;
    set[0].events = POLLIN;
    set[0].revents = 0;

    if (poll(&set[0], sizeof(set)/sizeof(*set), -1) < 0) {
      if (errno != EINTR) {
        perror("Poll failed:");
        continue;
      }
    }

    if (set[0].revents & POLLIN) {
      int sub_points[1];
      int reslen, i;
      confd_tag_value_t *vals;
      int flags = (CDB_GET_MODS_INCLUDE_LISTS|CDB_GET_MODS_SUPPRESS_DEFAULTS);

      if ((status = cdb_read_subscription_socket(subsock,&sub_points[0], &reslen)) != CONFD_OK) {
        //confd_fatal("terminate sub_read: %d\n", status);
        return CONFD_ERR;
      }

      if (cdb_get_modifications(subsock, sub_points[0], flags, &vals, &nvals, NULL) == CONFD_OK) {
#if 0
        print_tag_value_array(vals, nvals, NULL, 0);
#endif
        for (i = 0; i < nvals; i++) {
          confd_free_value(CONFD_GET_TAG_VALUE(&vals[i]));
        }
        free(vals);
      }
    }
    if ((status = cdb_sync_subscription_socket(subsock, CDB_DONE_OPERATIONAL)) != CONFD_OK) {
      confd_fatal("failed to sync subscription: %d\n", status);
    }
  }
  cdb_close(subsock);
  return CONFD_OK;
}

int main(int argc, char **argv) {
  int c;
  char *confd_addr = "127.0.0.1";
  int confd_port = CONFD_PORT;

  while ((c = getopt(argc, argv, "a:P:")) != -1) {
    switch(c) {
    case 'a':
      confd_addr = optarg;
      break;
    case 'P':
      confd_port = atoi(optarg);
      break;
    }
  }

  confd_init("cdb-sub", stderr, CONFD_SILENT);

  if(runtest(confd_addr, confd_port) != CONFD_OK)
    exit(1);
  exit(0);
}
