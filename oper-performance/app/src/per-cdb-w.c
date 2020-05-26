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

/* include generated file */
#include "routes.h"

#define SUBPATH "/r:routes"
#define LISTPATH SUBPATH"/route"

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

static int runtest(int n_list_entries, int max_nobjs, int iter)
{
  int i, j, pos, k, ret, rwsock, nobj, nvals;
  confd_tag_value_t *v;
  struct sockaddr_in addr;
  char id[n_list_entries][100];
  struct confd_cs_node *csnode;

  addr.sin_addr.s_addr = inet_addr("127.0.0.1");
  addr.sin_family = AF_INET;
  addr.sin_port = htons(CONFD_PORT);

  if (confd_load_schemas((struct sockaddr*)&addr, sizeof (struct sockaddr_in)) != CONFD_OK)
    confd_fatal("Failed to load schemas from confd\n");

  csnode = confd_cs_node_cd(NULL, LISTPATH);
  nvals = confd_max_object_size(csnode);

  if ((rwsock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open socket\n");

  if (cdb_connect(rwsock, CDB_DATA_SOCKET, (struct sockaddr*)&addr, sizeof (struct sockaddr_in)) < 0)
    return CONFD_ERR;

  for (i=0;i<iter;i++) {
    cdb_start_session2(rwsock, CDB_OPERATIONAL, CDB_LOCK_REQUEST | CDB_LOCK_WAIT | CDB_LOCK_PARTIAL);
    pos=0;
    while (pos < n_list_entries) {
      if (n_list_entries - pos > max_nobjs) {
        nobj = max_nobjs;
      } else {
        nobj = n_list_entries - pos;
      }
      j = 0;
      v = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * (nvals + 2) * nobj);
      for (k=0;k<nobj;k++) {
        sprintf(id[k], "%07d", pos);
        CONFD_SET_TAG_XMLBEGIN(&v[j], r_route, r__ns); j++;
        CONFD_SET_TAG_STR(&v[j], r_id, id[k]); j++;
        CONFD_SET_TAG_INT32(&v[j], r_leaf1, 1+pos); j++;
        CONFD_SET_TAG_INT32(&v[j], r_leaf2, 2); j++;
        CONFD_SET_TAG_INT32(&v[j], r_leaf3, 3); j++;
        CONFD_SET_TAG_INT32(&v[j], r_leaf4, 4); j++;
        CONFD_SET_TAG_XMLEND(&v[j], r_route, r__ns); j++;
        pos++;
      }
      if ((ret = cdb_set_values(rwsock, v, j, SUBPATH)) < 0) {
#if 0
        print_tag_value_array(v, j, NULL, 0);
#endif
        confd_fatal("cdb_set_values() failed ret=%d nobj=%d iter=%d j=%d pos=%d\n", ret, nobj, iter, j, pos);
      }
      free(v);
    }
    cdb_end_session(rwsock);
  }
  return cdb_close(rwsock);
}

int main(int argc, char **argv)
{
  int c;
  int n_list_entries = 1;
  int iter = 1;
  int max_nobjs = 100;

  while ((c = getopt(argc, argv, "n:i:x:")) != -1) {
    switch(c) {
    case 'n':
      n_list_entries = atoi(optarg);
      break;
    case 'x':
      max_nobjs = atoi(optarg);
      break;
    case 'i':
      iter = atoi(optarg);
      break;
    }
  }

  confd_init("cdb-writer", stderr, CONFD_SILENT);

  if(runtest(n_list_entries, max_nobjs, iter) != CONFD_OK)
      exit(1);
  exit(0);
}
