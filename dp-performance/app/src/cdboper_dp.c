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
#include <confd_dp.h>
#include <confd_cdb.h>
#include <confd.h>

static struct confd_cs_node *provide_from_root_node;

static int max_nobjs = 100;

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

/* Begin demo code */
/* Our daemon context as a global variable */
static struct confd_daemon_ctx *dctx;
static int ctlsock;
static int workersock;
static int cdbsock;

static void mk_kp_str(char *kp_str, int bufsiz, char *ns, confd_hkeypath_t *keypath)
{
  int kp_len = keypath->len - 1;
  confd_value_t *v = &(keypath->v[keypath->len - 1][0]);
  //confd_value_t *keys;
  int i, j, k, kp_strlen = 0; //nkeys
  char tmpbuf[confd_maxkeylen][BUFSIZ];
  struct confd_cs_node *cs_node;

  confd_pp_kpath(kp_str, bufsiz, keypath);
  for(i = kp_len; i >= 0; i--) {
    v = &(keypath->v[i][0]);
    if(v->type == C_XMLTAG) {
      confd_format_keypath(&kp_str[kp_strlen], bufsiz - kp_strlen, "/%s%s:%x", confd_ns2prefix(v->val.xmltag.ns), "-state", v);
    } else {
      cs_node = confd_cs_node_cd(NULL, &kp_str[0]);
      cs_node = cs_node->children;
      for(j = 0; keypath->v[i][j].type != C_NOEXISTS; j++) {
        confd_val2str(cs_node->info.type, &(keypath->v[i][j]), tmpbuf[j], sizeof(tmpbuf[j]));
        cs_node = cs_node->next;
      }
      strcpy(&kp_str[kp_strlen], "{"); kp_strlen++;
      for(k = 0; k < j; k++) {
        snprintf(&kp_str[kp_strlen], bufsiz - kp_strlen, "%s ", &(tmpbuf[k][0]));
        kp_strlen = strlen(kp_str);
      }
      strcpy(&kp_str[kp_strlen - 1], "}");
    }
    kp_strlen = strlen(kp_str);
  }
}

static int s_init(struct confd_trans_ctx *tctx)
{
  confd_trans_set_fd(tctx, workersock);
  return CONFD_OK;
}

static int num_instances(struct confd_trans_ctx *tctx,
                         confd_hkeypath_t *keypath)
{
  confd_value_t v;
  char kp_str[BUFSIZ];

  mk_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);
  CONFD_SET_INT32(&v, cdb_num_instances(cdbsock, "%s", kp_str));
  confd_data_reply_value(tctx, &v);

  return CONFD_OK;
}

static int get_case(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *kp, confd_value_t *choice)
{
  confd_value_t rcase;
  char kp_str[BUFSIZ];
  int ret; //,i;

  mk_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), kp);

  /*
  // TODO: NESTED CHOICES
  for(i = 0; &(v[i])->type != C_NOEXISTS; i++) {
    //handle
  }
  */

  if ((ret = cdb_get_case(cdbsock, confd_hash2str(CONFD_GET_XMLTAG(choice)),
                          &rcase, &kp_str[0])) == CONFD_ERR_NOEXISTS) {
    confd_data_reply_not_found(tctx);
  }
  rcase.val.xmltag.ns = choice->val.xmltag.ns;
  confd_data_reply_value(tctx, &rcase);
  return CONFD_OK;
}

static int traverse_cs_nodes(struct confd_cs_node *curr_cs_node, confd_tag_value_t *itv, int j)
{
  struct confd_cs_node *cs_node;
  int mask = (CS_NODE_IS_ACTION|CS_NODE_IS_PARAM|CS_NODE_IS_RESULT|
              CS_NODE_IS_NOTIF|CS_NODE_IS_LIST);
  for (cs_node = curr_cs_node; cs_node != NULL; cs_node = cs_node->next) {
    if (cs_node->info.flags & CS_NODE_IS_CONTAINER) {
      if (cs_node->info.minOccurs == 1) { // Skip presence containers
        CONFD_SET_TAG_XMLBEGIN(&itv[j], cs_node->tag, cs_node->ns); j++;
        j = traverse_cs_nodes(cs_node->children, itv, j);
        CONFD_SET_TAG_XMLEND(&itv[j], cs_node->tag, cs_node->ns); j++;
      }
    } else if ((cs_node->info.flags & mask) == 0) {
      CONFD_SET_TAG_NOEXISTS(&itv[j], cs_node->tag); j++;
    }
  }
  return j;
}

static int get_object(struct confd_trans_ctx *tctx,
                      confd_hkeypath_t *keypath)
{
  confd_tag_value_t *itv;
  int pos, j = 0, k;
  struct confd_cs_node *cs_node;
  char kp_str[BUFSIZ], *lastslash;

  mk_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);
  cs_node = confd_cs_node_cd(NULL, "%s", kp_str);
  itv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * 2 * (1 + confd_max_object_size(cs_node)));
  if (cs_node->info.flags & CS_NODE_IS_LIST) { /* list */
    pos = cdb_index(cdbsock, "%s", kp_str);
    if (pos < 0) {
      /* No list entry with a maching key */
      confd_data_reply_not_found(tctx);
      return CONFD_OK;
    }
    CONFD_SET_TAG_CDBBEGIN(&itv[j], cs_node->tag, cs_node->ns, pos); j++;
    j = traverse_cs_nodes(cs_node->children, &itv[0], j);
    CONFD_SET_TAG_XMLEND(&itv[j], cs_node->tag, cs_node->ns); j++;
  } else { /* container */
    j = traverse_cs_nodes(cs_node->children, &itv[0], j);
  }
  if((lastslash = strrchr(kp_str, '/')) != NULL) {
    if (lastslash != &kp_str[0]) {
      *lastslash = 0;
    }
  }
  if (cdb_get_values(cdbsock, itv, j, "%s", kp_str) != CONFD_OK) {
    confd_fatal("cdb_get_values() from path %s failed\n", kp_str);
  }

  /* Zero out the namespace */
  for(k = 0; k < j; k++) {
    itv[k].tag.ns = 0;
  }

  j-=2; /* no begin and end tags = two less tags */
  confd_data_reply_tag_value_array(tctx, &itv[1], j);
  confd_free_value(&itv[0].v); /* name must be freed since it's a C_BUF */
  free(itv);
  return CONFD_OK;
}

static int find_next(struct confd_trans_ctx *tctx,
                     confd_hkeypath_t *keypath,
                     enum confd_find_next_type type,
                     confd_value_t *keys, int nkeys)
{
  confd_value_t v[confd_maxkeylen];
  confd_tag_value_t tv[confd_maxkeylen];
  int pos = -1, i, j;
  u_int32_t *keyptr;
  struct confd_cs_node *cs_node;
  char kp_str[BUFSIZ], *lastslash;

  mk_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);

  cs_node = confd_cs_node_cd(NULL, "%s", kp_str);
  if (cs_node->info.flags & CS_NODE_IS_LEAF_LIST) {
    confd_data_reply_next_key(tctx, NULL, -1, -1);
    return CONFD_OK;
  }

  if (nkeys == 0) {
    pos = 0; /* first call */
  } else {
    switch (type) {
    case CONFD_FIND_SAME_OR_NEXT:
      if((pos = cdb_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys)) < 0) {
        pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
      }
      break;
    case CONFD_FIND_NEXT:
      pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
      break;
    default:
      confd_fatal("invalid find next type");
      break;
    }

    if (pos < 0) {
      /* key does not exist */
      confd_data_reply_next_key(tctx, NULL, -1, -1);
      return CONFD_OK;
    }
  }

  /* get the key */
  j = 0;
  CONFD_SET_TAG_CDBBEGIN(&tv[j], cs_node->tag, cs_node->ns, pos); j++;
  for (keyptr = cs_node->info.keys; *keyptr != 0; keyptr++) {
    CONFD_SET_TAG_NOEXISTS(&tv[j], *keyptr); j++;
  }
  CONFD_SET_TAG_XMLEND(&tv[j], cs_node->tag, cs_node->ns); j++;

  if((lastslash = strrchr(kp_str, '/'))) {
    if (lastslash != &kp_str[0]) {
      *lastslash = 0;
    }
  }
  if (cdb_get_values(cdbsock, tv, j, "%s", kp_str) != CONFD_OK) {
    /* key not found in the unlikely event that it was deleted after our
       cdb_index() check */
    confd_data_reply_next_key(tctx, NULL, -1, -1);
    return CONFD_OK;
  }

  for (i = 0; i < j-2; i++) {
    v[i].type = tv[i+1].v.type;
    v[i].val = tv[i+1].v.val;
  }
  /* reply */
  confd_data_reply_next_key(tctx, &v[0], j-2, pos+1);
  return CONFD_OK;
}

static int find_next_object(struct confd_trans_ctx *tctx,
                            confd_hkeypath_t *keypath,
                            enum confd_find_next_type type,
                            confd_value_t *keys, int nkeys)
{
  int pos = 0, n_list_entries, nobj, i, j, k, n;
  confd_tag_value_t *tv, *itv;
  struct confd_tag_next_object *tobj;
  struct confd_cs_node *cs_node;
  char kp_str[BUFSIZ], *lastslash;

  mk_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);

  cs_node = confd_cs_node_cd(NULL, "%s", kp_str);
  if (cs_node->info.flags & CS_NODE_IS_LEAF_LIST) {
    confd_data_reply_next_key(tctx, NULL, -1, -1);
    return CONFD_OK;
  }

  if (nkeys == 0) {
    pos = 0; /* first call */
  } else {
    switch (type) {
    case CONFD_FIND_SAME_OR_NEXT:
      if((pos = cdb_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys)) < 0) {
        pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
      }
      break;
    case CONFD_FIND_NEXT:
      pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
      break;
    default:
      confd_fatal("invalid find next type");
      break;
    }

    if (pos < 0) {
      /* key does not exist */
      confd_data_reply_next_key(tctx, NULL, -1, -1);
      return CONFD_OK;
    }
  }

  if (pos == -1 || (n_list_entries = cdb_num_instances(cdbsock, "%s", kp_str)) <= pos) {
    /* we have reached the end of the list */
    confd_data_reply_next_key(tctx, NULL, -1, -1);
    return CONFD_OK;
  }

  if (n_list_entries - pos > max_nobjs) {
    nobj = max_nobjs;
  } else {
    nobj = n_list_entries - pos;
  }

  /* get the list entries */
  itv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * nobj * 2 * (1 + confd_max_object_size(cs_node)));
  j = 0;
  for (i = 0; i < nobj; i++) {
    CONFD_SET_TAG_CDBBEGIN(&itv[j], cs_node->tag, cs_node->ns, pos+i); j++;
    j = traverse_cs_nodes(cs_node->children, &itv[0], j);
    CONFD_SET_TAG_XMLEND(&itv[j], cs_node->tag, cs_node->ns); j++;
  }

  if((lastslash = strrchr(kp_str, '/'))) {
    if (lastslash != &kp_str[0]) {
      *lastslash = 0;
    }
  }
  if (cdb_get_values(cdbsock, &itv[0], j, "%s", kp_str) != CONFD_OK) {
    confd_fatal("cdb_get_values() from path %s failed\n", kp_str);
  }

  tobj = malloc(sizeof(struct confd_tag_next_object) * (max_nobjs + 1));
  tv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * max_nobjs * 2 * (1 + confd_max_object_size(cs_node)));

  /* create reply */
  j = j/nobj - 2; /* no begin and end tags for exach object */
  n = 0;
  for (i = 0; i < nobj; i++) {
    tobj[i].tv = &tv[i * j];
    n++; /* get rid of the begin list tag */
    for(k = 0; k < j; k++) {
      CONFD_SET_TAG_VALUE(&(tobj[i].tv[k]), itv[n].tag.tag, &itv[n].v); n++;
    }
    n++; /* dispose of the end list tag */
    tobj[i].n = j;
    tobj[i].next = (long)pos+i+1;
  }

  if (pos + i >= n_list_entries)
    tobj[i++].tv = NULL; /* indicate no more list entries */

  /* reply */
  confd_data_reply_next_object_tag_value_arrays(tctx, tobj, i, 0);
  //for (i = 0; pos + i < nobj; i++) {
  //  confd_free_value(CONFD_GET_TAG_VALUE(&(tobj[i].tv[0]))); /* name must be freed since it's a C_BUF */
  //}
  free(itv);
  free(tv);
  free(tobj);
    return CONFD_OK;
}

int main(int argc, char *argv[])
{
  struct sockaddr_in addr;
  int c, debuglevel = CONFD_DEBUG, flags;
  struct confd_trans_cbs trans;
  struct confd_data_cbs data;
  char *confd_ip = "127.0.0.1";
  int confd_port = CONFD_PORT;
  char *callpoint = NULL;
  char *provide_from_root_node_path = NULL;

  while ((c = getopt(argc, argv, "a:p:P:i:c:x:drts")) != EOF) {
    switch(c) {
    case 'a':
      confd_ip = optarg;
      break;
    case 'P':
      confd_port = atoi(optarg);
      break;
    case 'p':
      provide_from_root_node_path = optarg;
      break;
    case 'c':
      callpoint = optarg;
      break;
    case 'x':
      max_nobjs = atoi(optarg);
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

  /* Initialize confd library */
  confd_init("oper-data-reader", stderr, debuglevel);

  if (provide_from_root_node_path == NULL || callpoint == NULL )
    confd_fatal("Need a root node to provide data from, -P \"/path/to/root/node\", and a callpoint name, -c \"my-callpoint\"\n");

  addr.sin_addr.s_addr = inet_addr(confd_ip);
  addr.sin_family = AF_INET;
  addr.sin_port = htons(confd_port);

  if (confd_load_schemas((struct sockaddr*)&addr,
                         sizeof (struct sockaddr_in)) != CONFD_OK)
    confd_fatal("Failed to load schemas from confd\n");

  provide_from_root_node = confd_cs_node_cd(NULL, provide_from_root_node_path);

  if ((dctx = confd_init_daemon("cdb-oper-provider")) == NULL)
    confd_fatal("Failed to initialize daemon\n");
  flags = CONFD_DAEMON_FLAG_BULK_GET_CONTAINER;
  if (confd_set_daemon_flags(dctx, flags) != CONFD_OK)
    confd_fatal("Failed to set daemon flags\n");

  /* Create and connect the control and worker sockets */
  if ((ctlsock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open ctlsocket\n");
  if (confd_connect(dctx, ctlsock, CONTROL_SOCKET, (struct sockaddr*)&addr,
                    sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to confd_connect() to confd \n");

  if ((workersock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open workersocket\n");
  if (confd_connect(dctx, workersock, WORKER_SOCKET,(struct sockaddr*)&addr,
                    sizeof (struct sockaddr_in)) < 0)
    confd_fatal("Failed to confd_connect() to confd \n");

  /* Register callbacks */
  memset(&trans, 0, sizeof(trans));
  trans.init = s_init;
  if (confd_register_trans_cb(dctx, &trans) == CONFD_ERR)
    confd_fatal("Failed to register trans cb\n");

  memset(&data, 0, sizeof (struct confd_data_cbs));
  /* assuming large lists and not the content of
     individual leafs are typically requested */
  data.num_instances = num_instances;
  data.get_case = get_case;
  data.get_object = get_object;
  data.find_next = find_next;
  data.find_next_object = find_next_object;

  strcpy(data.callpoint, callpoint);
  if (confd_register_data_cb(dctx, &data) == CONFD_ERR)
    confd_fatal("Failed to register data cb\n");

  if (confd_register_done(dctx) != CONFD_OK)
    confd_fatal("Failed to complete registration \n");

  /* Start a CDB session towards the CDB operational datastore */
  if ((cdbsock = socket(PF_INET, SOCK_STREAM, 0)) < 0)
    confd_fatal("Failed to create the CDB socket");
  if (cdb_connect(cdbsock, CDB_DATA_SOCKET, (struct sockaddr *)&addr,
                  sizeof(struct sockaddr_in)) < 0)
    confd_fatal("Failed to connect to ConfD CDB");
  if (cdb_start_session(cdbsock, CDB_OPERATIONAL) != CONFD_OK)
    confd_fatal("Failed to start a CDB session\n");
  if (cdb_set_namespace(cdbsock, provide_from_root_node->ns) != CONFD_OK)
    confd_fatal("Failed to set namespace\n");

  while(1) {
    struct pollfd set[2];
    int ret;

    set[0].fd = ctlsock;
    set[0].events = POLLIN;
    set[0].revents = 0;

    set[1].fd = workersock;
    set[1].events = POLLIN;
    set[1].revents = 0;

    if (poll(set, sizeof(set)/sizeof(set[0]), -1) < 0) {
      perror("Poll failed:");
      continue;
    }

    /* Check for I/O */
    if (set[0].revents & POLLIN) {
      if ((ret = confd_fd_ready(dctx, ctlsock)) == CONFD_EOF) {
        confd_fatal("Control socket closed\n");
      } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
        confd_fatal("Error on control socket request: %s (%d): %s\n",
                    confd_strerror(confd_errno), confd_errno, confd_lasterr());
      }
    }
    if (set[1].revents & POLLIN) {
      if ((ret = confd_fd_ready(dctx, workersock)) == CONFD_EOF) {
        confd_fatal("Worker socket closed\n");
      } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
        confd_fatal("Error on worker socket request: %s (%d): %s\n",
                    confd_strerror(confd_errno), confd_errno, confd_lasterr());
      }
    }
  }
}
