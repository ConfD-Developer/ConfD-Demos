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

static int entries_per_request = 100;
static int tv_alloc_len = 0;
static confd_tag_value_t *tvs = NULL;
#define TV_BUF_LEN 1024

/* Tag value print helper function */
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
        printf("%*s%s %s\n", indent, "",
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

static void free_tag_values(confd_tag_value_t *tv, int n)
{
    int i;

    for (i = 0; i < n; i++) {
        confd_free_value(CONFD_GET_TAG_VALUE(&tv[i]));
    }
}

/* Begin demo code */
static int traverse_cs_nodes(int ms, int th, int j, char *path, struct confd_cs_node *curr_cs_node, confd_value_t *values, int keyleafs)
{
  int nkeys = 0, tot_nobjs, nobjs, curr_nobjs, i, nsubvals, ret, len, sublen, tmpj;
  u_int32_t *keyptr;
  int mask = (CS_NODE_IS_ACTION|CS_NODE_IS_PARAM|CS_NODE_IS_RESULT|
              CS_NODE_IS_NOTIF);
  confd_value_t *subvals;
  struct maapi_cursor mc;
  struct confd_cs_node *cs_node;

  if (j > (tv_alloc_len / 2)) {
    tv_alloc_len *= 2;
    tvs = (confd_tag_value_t *) realloc(tvs, sizeof(confd_tag_value_t) * tv_alloc_len);
  }

  len = strlen(path);
  int nval = 0;
  for (cs_node = curr_cs_node; cs_node != NULL; cs_node = cs_node->next, nval++) {
    snprintf(&path[len], BUFSIZ - len, "/%s:%s", confd_ns2prefix(cs_node->ns), confd_hash2str(cs_node->tag));
    if (cs_node->info.flags & CS_NODE_IS_LIST) {
      nsubvals = confd_max_object_size(cs_node);
      tot_nobjs = maapi_num_instances(ms, th, path);
      subvals = malloc(sizeof(confd_value_t) * nsubvals * tot_nobjs);
      curr_nobjs = 0;
      maapi_init_cursor(ms, th, &mc, path);
      nobjs = entries_per_request;
      do {
        ret = maapi_get_objects(&mc, &subvals[curr_nobjs * nsubvals], nsubvals, &nobjs);
        curr_nobjs += nobjs;
      } while (ret >= 0 && mc.n != 0);
      maapi_destroy_cursor(&mc);
      nkeys = 0;
      for (keyptr = cs_node->info.keys; keyptr != NULL && *keyptr != 0; keyptr++) {
        nkeys++;
      }
      sublen = strlen(path);
      for (i = 0; i < tot_nobjs; i++) {
        confd_format_keypath(&path[sublen], BUFSIZ - sublen, "{%*x}", nkeys, &subvals[i * nsubvals]);
        CONFD_SET_TAG_XMLBEGIN(&tvs[j], cs_node->tag, cs_node->ns); j++;
        tmpj = j;
        j = traverse_cs_nodes(ms, th, j, path, cs_node->children, &subvals[i * nsubvals], nkeys);
        if (j == tmpj) {
          j--;
        } else {
          CONFD_SET_TAG_XMLEND(&tvs[j], cs_node->tag, cs_node->ns); j++;
        }
      }
      free(subvals);
    } else if (cs_node->info.flags & CS_NODE_IS_CONTAINER) {
      nsubvals = confd_max_object_size(cs_node);
      subvals = malloc(sizeof(confd_value_t) * nsubvals);
      maapi_get_object(ms, th, subvals, nsubvals, path);

      CONFD_SET_TAG_XMLBEGIN(&tvs[j], cs_node->tag, cs_node->ns); j++;
      tmpj = j;
      j = traverse_cs_nodes(ms, th, j, path, cs_node->children, subvals, 0);
      if (j == tmpj) {
        j--;
      } else {
        CONFD_SET_TAG_XMLEND(&tvs[j], cs_node->tag, cs_node->ns); j++;
      }
      free(subvals);
    } else if ((cs_node->info.flags & mask) == 0) {
      if (values != NULL) {
        if ((cs_node->info.flags & CS_NODE_IS_WRITE) == 0 || keyleafs > 0) {
          CONFD_SET_TAG_VALUE(&tvs[j], cs_node->tag, &values[nval]); j++;
          if (keyleafs > 0)
            keyleafs--;
        }
      } else {
        confd_fatal("A root node must be a container or list node, not a leaf node\n");
      }
    }
    path[len] = 0;
  }
  return j;
}

int main(int argc, char *argv[])
{
  struct sockaddr_in addr;
  int c, thandle, maapisock, j, ret;
  struct confd_cs_node *cs_node;
  struct confd_ip ip;
  const char *user = "admin", *groups[] = { "admin" }, *context = "system";
  char path[BUFSIZ], *lastslash;
  char *confd_ip = "127.0.0.1";
  int confd_port = CONFD_PORT;
  int debuglevel = CONFD_DEBUG;
  int datastore = CONFD_RUNNING;

  strcpy(&path[0], "/r:sys");

  while ((c = getopt(argc, argv, "a:p:u:g:c:P:e:CROdrts")) != EOF) {
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
      strcpy(&path[0], (char *)optarg);
      break;
    case 'e':
      entries_per_request = atoi(optarg);
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

  if ((thandle = maapi_start_trans(maapisock, datastore,
                                   CONFD_READ)) < 0) {
    confd_fatal("Failed to start trans\n");
  }

  if ((ret = maapi_set_flags(maapisock, thandle, 0)) != CONFD_OK) {
    confd_fatal("maapi_set_flags() failed\n");
  }

  cs_node = confd_cs_node_cd(NULL, &path[0]);
  tv_alloc_len = TV_BUF_LEN;
  tvs = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * tv_alloc_len);
  j = 0;
  if((lastslash = strrchr(&path[0], '/')) != NULL) {
    *lastslash = 0;
  }

  j = traverse_cs_nodes(maapisock, thandle, j, &path[0], cs_node, NULL, 0);

  print_tag_value_array(tvs, j, cs_node, 0);
  free_tag_values(tvs,j);
  free(tvs);
}
