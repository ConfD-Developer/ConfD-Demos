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

/* Debug tag value print helper functions */
#define BUFF_LEN 65536
#define INDENT_SIZE 4
#define INDENT_STR ""

struct pr_doc {
    size_t alloc_len;
    int len;
    char *data;
};

static void doc_init(struct pr_doc *document)
{
    document->alloc_len = BUFF_LEN;
    document->len = 0;
    document->data = malloc(document->alloc_len);
    memset(document->data, 0x00, document->alloc_len);
}

static int doc_append(struct pr_doc *document, char *str)
{
    size_t str_len = strnlen(str, BUFF_LEN);
    size_t remaining_len = (document->alloc_len - document->len);

    if (str_len > remaining_len) {
        document->data = realloc(document->data,
                            document->alloc_len + BUFF_LEN);
    }

    strncpy(document->data + document->len, str, str_len);
    document->len += str_len;

    return str_len;
}

/* For debug purposes - print a tag_value */
static int write_tag_value(struct pr_doc *document, confd_tag_value_t *tag_val,
        int *indent)
{
    char *tag_str = confd_xmltag2str(tag_val->tag.ns, tag_val->tag.tag);

    char buff[BUFF_LEN+7];
    char value_buff[BUFF_LEN];

    switch (tag_val->v.type) {
        // start a container/list entry creation/modification
        case C_XMLBEGIN:
            snprintf(buff, sizeof(buff), "%*s<%s>\n", *indent, INDENT_STR,
                    tag_str);
            *indent += INDENT_SIZE;
            break;
        // start a container/list entry creation/modification based on index
        case C_CDBBEGIN:
            snprintf(buff, sizeof(buff), "%*s<%s>\n", *indent, INDENT_STR,
                    tag_str);
            *indent += INDENT_SIZE;
            break;
        // exit from a processing of container/list entry creation/modification
        case C_XMLEND:
            *indent -= INDENT_SIZE;
            snprintf(buff, sizeof(buff), "%*s</%s>\n", *indent, INDENT_STR,
                    tag_str);
            break;
        // deletion of a leaf
        case C_NOEXISTS:
            snprintf(buff, sizeof(buff), "%*s<%s operation=\"delete\">\n",
                    *indent, INDENT_STR, tag_str);
            break;
        // deletion of a list entry / container
        case C_XMLBEGINDEL:
            snprintf(buff, sizeof(buff), "%*s<%s operation=\"delete\">\n",
                    *indent, INDENT_STR, tag_str);
            *indent += INDENT_SIZE;
            break;
        // type empty leaf creation
        case C_XMLTAG:
            snprintf(buff, sizeof(buff), "%*s<%s/>\n", *indent, INDENT_STR,
                    tag_str);
            break;
        // regular leaf creation/modification
        default:
            confd_pp_value(value_buff, sizeof(value_buff), &tag_val->v);
            snprintf(buff, sizeof(buff), "%*s<%s>%s</%s>\n", *indent,
                    INDENT_STR, tag_str, value_buff, tag_str);
    }

    int chars_written = doc_append(document, buff);
    return chars_written;
}

/* For debug purposes - print a tag value array */
char * print_tag_value_array(
    confd_tag_value_t *tvs,
    int tvs_cnt
) {
    struct pr_doc doc;
    doc_init(&doc);

    int indent = 0;

    int i;
    for (i = 0; i <tvs_cnt; i++) {
        write_tag_value(&doc, &tvs[i], &indent);
    }

    return doc.data;
}

/* Begin demo code */
/* Our daemon context as a global variable */
static struct confd_daemon_ctx *dctx;
static int ctlsock;
static int workersock;
static int cdbsock;

static void mk_oper_kp_str(char *kp_str, int bufsiz, char *ns, confd_hkeypath_t *keypath)
{
  int kp_len = keypath->len - 1;
  confd_value_t *v = &(keypath->v[keypath->len - 1][0]);
  confd_value_t *keys;
  int i, j, nkeys, kp_strlen = 0;

  confd_pp_kpath(kp_str, bufsiz, keypath);
  for(i = kp_len; i >= 0; i--) {
    v = &(keypath->v[i][0]);
    if(v->type == C_XMLTAG) {
      confd_format_keypath(&kp_str[kp_strlen], bufsiz - kp_strlen, "/%s%s:%x", confd_ns2prefix(v->val.xmltag.ns), "-state", v);
    } else {
      nkeys = 0;
      for(j = 0; keypath->v[i][j].type != C_NOEXISTS; j++)
        nkeys++;
      if (nkeys > 0) {
        kp_strlen = strlen(kp_str);
        keys = &(keypath->v[i][0]);
        confd_format_keypath(&kp_str[kp_strlen], bufsiz - kp_strlen, "{%*x}", nkeys, keys);
      }
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

  mk_oper_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);
  CONFD_SET_INT32(&v, cdb_num_instances(cdbsock, "%s", kp_str));
  confd_data_reply_value(tctx, &v);

  return CONFD_OK;
}

static int traverse_cs_nodes(struct confd_cs_node *curr_cs_node, confd_tag_value_t *itv, int j)
{
  //TODO: Handle oper data in choices and presence containers
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

  mk_oper_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);
  cs_node = confd_cs_node_cd(NULL, "%s", kp_str);
  itv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * 2 * confd_max_object_size(cs_node));
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
  //fprintf(stderr, "GET VALUES\n%s\n", print_tag_value_array(&itv[0],j));
  if((lastslash = strrchr(kp_str, '/')) != NULL)
    if (lastslash != &kp_str[0])
      *lastslash = 0;
  if (cdb_get_values(cdbsock, itv, j, "%s", kp_str) != CONFD_OK) {
    confd_fatal("cdb_get_values() from path %s failed\n", kp_str);
  }
  //fprintf(stderr, "VALUES RECEIVED\n%s\n", print_tag_value_array(&itv[0],j));

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
  confd_value_t v;
  confd_tag_value_t tv[confd_maxkeylen];
  int pos = -1, j;
  u_int32_t *keyptr;
  struct confd_cs_node *cs_node;
  char kp_str[BUFSIZ], *lastslash;
  mk_oper_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);

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
  cs_node = confd_cs_node_cd(NULL, "%s", kp_str);
  j = 0;
  CONFD_SET_TAG_CDBBEGIN(&tv[j], cs_node->tag, cs_node->ns, pos); j++;
  for (keyptr = cs_node->info.keys; *keyptr != 0; keyptr++) {
    CONFD_SET_TAG_NOEXISTS(&tv[j], *keyptr); j++;
  }
  CONFD_SET_TAG_XMLEND(&tv[j], cs_node->tag, cs_node->ns); j++;

  if((lastslash = strrchr(kp_str, '/')))
    *lastslash = 0;
  if (cdb_get_values(cdbsock, tv, 3, "%s", kp_str) != CONFD_OK) {
    /* key not found in the unlikely event that it was deleted after our
       cdb_index() check */
    confd_data_reply_next_key(tctx, NULL, -1, -1);
    return CONFD_OK;
  }

  CONFD_SET_STR(&v, CONFD_GET_CBUFPTR(CONFD_GET_TAG_VALUE(&tv[1])));

  /* reply */
  confd_data_reply_next_key(tctx, &v, 1, pos+1);
  confd_free_value(&v);

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

  mk_oper_kp_str(&kp_str[0], BUFSIZ, confd_ns2prefix(provide_from_root_node->ns), keypath);

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

  //fprintf(stderr, "\nn_list_entries %d nobj %d pos %d nkeys %d\n", n_list_entries, nobj, pos, nkeys);

  /* get the list entries */
  cs_node = confd_cs_node_cd(NULL, "%s", kp_str);
  itv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * nobj * 2 * confd_max_object_size(cs_node));
  j = 0;
  for (i = 0; i < nobj; i++) {
    CONFD_SET_TAG_CDBBEGIN(&itv[j], cs_node->tag, cs_node->ns, pos+i); j++;
    j = traverse_cs_nodes(cs_node->children, &itv[0], j);
    CONFD_SET_TAG_XMLEND(&itv[j], cs_node->tag, cs_node->ns); j++;
  }

  if((lastslash = strrchr(kp_str, '/')))
    *lastslash = 0;
  //fprintf(stderr, "GET VALUES\n%s\n", print_tag_value_array(&itv[0],j));
  if (cdb_get_values(cdbsock, itv, j, "%s", kp_str) != CONFD_OK) {
    confd_fatal("cdb_get_values() from path %s failed\n", kp_str);
  }
  //fprintf(stderr, "VALUES RECEIVED\n%s\n", print_tag_value_array(&itv[0],j));

  tobj = malloc(sizeof(struct confd_tag_next_object) * (max_nobjs + 1));
  tv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * max_nobjs * 2 * confd_max_object_size(cs_node));

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
  for (i = 0; pos + i < nobj; i++) {
    confd_free_value(CONFD_GET_TAG_VALUE(&(tobj[i].tv[0]))); /* name must be freed since it's a C_BUF */
  }
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
