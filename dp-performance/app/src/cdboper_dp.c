#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/poll.h>
#include <inttypes.h>
#include <limits.h>

#include <confd_lib.h>
#include <confd_dp.h>
#include <confd_cdb.h>
#include <confd_maapi.h>
#include <confd.h>

#define KP_MOD "-state"

static int max_nobjs = 100;
static FILE *estream;

/* Tag value print helper function */
#if 0
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
            snprintf(buff, sizeof(buff), "%*s<%s:%s>\n", *indent, INDENT_STR,
                    confd_ns2prefix(CONFD_GET_TAG_NS(tag_val)), tag_str);
            *indent += INDENT_SIZE;
            break;
        // start a container/list entry creation/modification based on index
        case C_CDBBEGIN:
            snprintf(buff, sizeof(buff), "%*s<%s:%s>\n", *indent, INDENT_STR,
                    confd_ns2prefix(CONFD_GET_TAG_NS(tag_val)), tag_str);
            *indent += INDENT_SIZE;
            break;
        // exit from a processing of container/list entry creation/modification
        case C_XMLEND:
            *indent -= INDENT_SIZE;
            snprintf(buff, sizeof(buff), "%*s</%s:%s>\n", *indent, INDENT_STR,
                    confd_ns2prefix(CONFD_GET_TAG_NS(tag_val)), tag_str);
            break;
        // deletion of a leaf
        case C_NOEXISTS:
            snprintf(buff, sizeof(buff), "%*s<%s:%s operation=\"noexists\">\n",
                    *indent, INDENT_STR,
                    confd_ns2prefix(CONFD_GET_TAG_NS(tag_val)), tag_str);
            break;
        // deletion of a list entry / container
        case C_XMLBEGINDEL:
            snprintf(buff, sizeof(buff), "%*s<%s operation=\"xmlbegindel\">\n",
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
            snprintf(buff, sizeof(buff), "%*s<%s:%s>%s</%s:%s>\n", *indent,
                    INDENT_STR, confd_ns2prefix(CONFD_GET_TAG_NS(tag_val)),
                    tag_str, value_buff,
                    confd_ns2prefix(CONFD_GET_TAG_NS(tag_val)), tag_str);
    }

    int chars_written = doc_append(document, buff);
    return chars_written;
}

/* For debug purposes - print a tag value array */
static void print_tag_value_array(confd_tag_value_t *tvs, int tvs_cnt,
                                  void *dummy, int dummy2)
{
    struct pr_doc doc;
    doc_init(&doc);

    int indent = 0;

    int i;
    for (i = 0; i <tvs_cnt; i++) {
        write_tag_value(&doc, &tvs[i], &indent);
    }
    fprintf(estream, "\n%s\n", doc.data);fflush(estream);
}
#endif

/* Begin demo code */
/* Our daemon context as a global variable */
static struct confd_daemon_ctx *dctx;
static int ctlsock;
static int workersock;
static int cdbsock;

static void mk_kp_str(char *kp_str, int bufsiz, confd_hkeypath_t *keypath,
                      char *kpmod)
{
  int kp_len = keypath->len - 1;
  confd_value_t *v = &(keypath->v[keypath->len - 1][0]);
  int i, j, k, kp_strlen = 0;
  char tmpbuf[confd_maxkeylen][BUFSIZ];
  struct confd_cs_node *cs_node;
  struct confd_type *type;
  u_int64_t pseudo_key = -1;

  //confd_pp_kpath(kp_str, bufsiz, keypath);
  //fprintf(stderr, "\nKP_STR\n %s",kp_str);
  for(i = kp_len; i >= 0; i--) {
    v = &(keypath->v[i][0]);
    if (v->type == C_XMLTAG) {
      confd_format_keypath(&kp_str[kp_strlen], bufsiz - kp_strlen,
                          "/%s%s:%x", confd_ns2prefix(v->val.xmltag.ns), kpmod,
                          v);
    } else {
      cs_node = confd_cs_node_cd(NULL, &kp_str[0]);
      if (cs_node->info.flags & CS_NODE_IS_LEAF_LIST) {
        type = confd_get_leaf_list_type(cs_node);
      } else {
        cs_node = cs_node->children;
        type = cs_node->info.type;
      }
      if (cs_node->parent->info.keys == NULL &&
          cs_node->parent->info.flags & CS_NODE_IS_LIST) {
        /* keyless list - get the pseudo key */
        pseudo_key = CONFD_GET_INT64(&(keypath->v[i][0]));
        snprintf(&(tmpbuf[0][0]), BUFSIZ, "%" PRIu64"", pseudo_key);
        j = 1;
      } else {
        for (j = 0; keypath->v[i][j].type != C_NOEXISTS; j++) {
          if (keypath->v[i][j].type == C_BUF) {
            /* Double quote all keys values of type string in case of embedded
               whitespace in key value */
            tmpbuf[j][0] = '\"';
            confd_val2str(type, &(keypath->v[i][j]), &(tmpbuf[j][1]), BUFSIZ);
            k = strlen(&(tmpbuf[j][1]));
            tmpbuf[j][k+1] = '\"';
            tmpbuf[j][k+2] = '\0';
          } else {
            confd_val2str(type, &(keypath->v[i][j]), &(tmpbuf[j][0]), BUFSIZ);
          }
          if ((cs_node->info.flags & CS_NODE_IS_LEAF_LIST) == 0 &&
              cs_node->next != NULL) {
            cs_node = cs_node->next;
            type = cs_node->info.type;
          }
        }
      }
      strcpy(&kp_str[kp_strlen], "{"); kp_strlen++;
      for (k = 0; k < j; k++) {
        snprintf(&kp_str[kp_strlen], bufsiz - kp_strlen, "%s ",
                 &(tmpbuf[k][0]));
        kp_strlen = strlen(kp_str);
      }
      strcpy(&kp_str[kp_strlen - 1], "}");
    }
    kp_strlen = strlen(kp_str);
  }
}

static int t_init(struct confd_trans_ctx *tctx)
{
  confd_trans_set_fd(tctx, workersock);
  return CONFD_OK;
}

static int exists_optional(struct confd_trans_ctx *tctx,
                           confd_hkeypath_t *keypath)
{
  char kp_str[BUFSIZ];
  int ret;

  mk_kp_str(&kp_str[0], BUFSIZ, keypath, KP_MOD);
  if ((ret = cdb_exists(cdbsock, &kp_str[0])) == 1) {
    confd_data_reply_found(tctx);
  } else {
    confd_data_reply_not_found(tctx);
  }
  return CONFD_OK;
}

static int get_case(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *kp, confd_value_t *choice)
{
  confd_value_t rcase;
  char kp_str[BUFSIZ];
  char choice_str[BUFSIZ];
  char *ns_str;
  char tmp_str[BUFSIZ];
  int ret, i, len = 0;

  mk_kp_str(&kp_str[0], BUFSIZ, kp, KP_MOD);
  for(len = 0; choice[len].type != C_NOEXISTS; len++);
  for(i = len-1; i >= 0; i--) {
    ns_str = confd_ns2prefix(CONFD_GET_XMLTAG_NS(&choice[i]));
    confd_pp_value(tmp_str, BUFSIZ, &choice[i]);
    snprintf(choice_str, sizeof(choice_str)-1,"%s%s:%s", ns_str, KP_MOD,
             tmp_str);
    if (i > 0) {
      strcat(&choice_str[0], "/");
    }
  }
  if ((ret = cdb_get_case(cdbsock, &choice_str[0],
                          &rcase, &kp_str[0])) != CONFD_OK ) {
    confd_data_reply_not_found(tctx);
  } else {
    rcase.val.xmltag.ns = choice->val.xmltag.ns;
    confd_data_reply_value(tctx, &rcase);
  }
  return CONFD_OK;
}

static int num_instances(struct confd_trans_ctx *tctx,
                         confd_hkeypath_t *keypath)
{
  confd_value_t v;
  char kp_str[BUFSIZ];

  mk_kp_str(&kp_str[0], BUFSIZ, keypath, KP_MOD);
  CONFD_SET_INT32(&v, cdb_num_instances(cdbsock, kp_str));
  confd_data_reply_value(tctx, &v);

  return CONFD_OK;
}

static int traverse_cs_nodes(struct confd_cs_node *curr_cs_node,
                             confd_tag_value_t *itv, int j)
{
  struct confd_cs_node *cs_node;
  int lmask = (CS_NODE_IS_ACTION|CS_NODE_IS_PARAM|CS_NODE_IS_RESULT|
               CS_NODE_IS_NOTIF|CS_NODE_IS_LIST);
  int cmask = (CS_NODE_IS_CONTAINER);
  for (cs_node = curr_cs_node; cs_node != NULL; cs_node = cs_node->next) {
    if (cs_node->info.flags & cmask) {
      CONFD_SET_TAG_XMLBEGIN(&itv[j], cs_node->tag, cs_node->ns); j++;
      j = traverse_cs_nodes(cs_node->children, itv, j);
      CONFD_SET_TAG_XMLEND(&itv[j], cs_node->tag, cs_node->ns); j++;
    } else if ((cs_node->info.flags & lmask) == 0) {
      CONFD_SET_TAG_NOEXISTS(&itv[j], cs_node->tag);
      CONFD_SET_TAG_NS(&itv[j], cs_node->ns); j++;
    }
  }
  return j;
}

static int format_object(confd_tag_value_t *tv, confd_tag_value_t *itv,
                         int n_itv, struct confd_cs_node *start)
{
  struct confd_cs_node *cs_node;
  char *prefix;
  int len, mod_len;
  int i, n = 0;
  for (i = 0; i < n_itv; i++) {
    if (CONFD_GET_TAG_VALUE(&itv[i])->type != C_NOEXISTS) {
      prefix = confd_ns2prefix(CONFD_GET_TAG_NS(&itv[i]));
      len = strlen(prefix);
      mod_len = strlen(KP_MOD);
      if (strcmp(&(prefix[len-mod_len]), KP_MOD) == 0) {
        prefix[len-mod_len] = '\0';
      }
      if (CONFD_GET_TAG_VALUE(&itv[i])->type == C_XMLEND) {
        if (start->parent == NULL) {
          start = confd_find_cs_root(start->ns);
        } else {
          start = start->parent;
        }
      }
      cs_node = confd_cs_node_cd(start, "%s:%s", prefix,
                                 confd_hash2str(CONFD_GET_TAG_TAG(&itv[i])));
      CONFD_SET_TAG_VALUE(&tv[n], CONFD_GET_TAG_TAG(&itv[i]),
                          CONFD_GET_TAG_VALUE(&itv[i]));
      CONFD_SET_TAG_NS(&tv[n], cs_node->ns);
      if (CONFD_GET_TAG_VALUE(&itv[i])->type == C_XMLBEGIN) {
        start = cs_node;
      }
      n++;
    }
  }
  return n;
}

static char* strrstr(const char *haystack, const char *needle)
{
  char *r = NULL;

  if (!needle[0])
    return (char*)haystack + strlen(haystack);
  while (1) {
    char *p = strstr(haystack, needle);
    if (!p)
      return r;
    r = p;
    haystack = p + 1;
  }
}

static int get_object(struct confd_trans_ctx *tctx,
                      confd_hkeypath_t *keypath)
{
  confd_tag_value_t *itv, *tv;
  int j = 0, n;
  struct confd_cs_node *cs_node, *start;
  char kp_str[BUFSIZ];

  start = confd_find_cs_node(keypath, keypath->len);
  mk_kp_str(&kp_str[0], BUFSIZ, keypath, KP_MOD);
  cs_node = confd_cs_node_cd(NULL, kp_str);
  itv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * 2 *
                                     (1 + confd_max_object_size(cs_node)));
  j = traverse_cs_nodes(cs_node->children, &itv[0], j);
  if (cdb_get_values(cdbsock, itv, j, kp_str) != CONFD_OK) {
    confd_data_reply_not_found(tctx);
    return CONFD_OK;
    //confd_fatal("cdb_get_values() from path %s failed\n", kp_str);
  }
  tv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * 2 *
                                    (1 + confd_max_object_size(cs_node)));
  n = format_object(tv, &itv[0], j, start);
  confd_data_reply_tag_value_array(tctx, tv, n);

  free(tv);
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
  int pos = -1, i, j, real_nkeys = 0;
  u_int32_t *keyptr;
  struct confd_cs_node *cs_node;
  char kp_str[BUFSIZ], stars[BUFSIZ];

  mk_kp_str(&kp_str[0], BUFSIZ, keypath, KP_MOD);

  cs_node = confd_cs_node_cd(NULL, kp_str);
  if (cs_node->info.flags & CS_NODE_IS_LEAF_LIST) {
    confd_value_t *list;
    int n_list, pos, ret;

    if ((ret = cdb_get(cdbsock, &v[0], kp_str)) != CONFD_OK) {
      confd_data_reply_next_key(tctx, NULL, -1, -1);
    } else {
    list = CONFD_GET_LIST(&v[0]);
      n_list = CONFD_GET_LISTSIZE(&v[0]);
      if (nkeys == 0) {
        confd_data_reply_next_key(tctx, list, 1, -1);
      } else {
        pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
        if (pos == -1) {
          confd_data_reply_next_key(tctx, NULL, -1, -1);
        } else {
          confd_data_reply_next_key(tctx, &list[pos], 1, -1);
        }
      }
      if (n_list > 0) {
        confd_free_value(list);
      }
    }
    return CONFD_OK;
  }

  for (keyptr = cs_node->info.keys; keyptr != NULL && *keyptr != 0; keyptr++) {
    real_nkeys++;
  }
  stars[0] = 0;
  for (i = 0; i < real_nkeys-nkeys; i++) {
    strcat(&stars[0], " *");
  }
  if (nkeys == 0) {
    pos = 0; /* first call */
  } else {
    switch (type) {
    case CONFD_FIND_SAME_OR_NEXT:
      if (real_nkeys - nkeys == 0) {
        if((pos = cdb_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys)) < 0) {
          pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
        }
      } else {
        pos = cdb_next_index(cdbsock, "%s{%*x%s}", kp_str, nkeys, keys, stars);
      }
      break;
    case CONFD_FIND_NEXT:
      pos = cdb_next_index(cdbsock, "%s{%*x%s}", kp_str, nkeys, keys, stars);
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
  if (real_nkeys == 0) { /* keyless list */
    CONFD_SET_INT64(&v[0], pos); j++;
  } else {
    ssize_t bufsz = snprintf(NULL, 0, "[%d]", pos);
    char tmp_str[bufsz + 1];
    snprintf(&tmp_str[0], sizeof(tmp_str), "[%d]", pos);
    strcat(&kp_str[0], &tmp_str[0]);
    for (keyptr = cs_node->info.keys; keyptr != NULL && *keyptr != 0; keyptr++) {
      CONFD_SET_TAG_NOEXISTS(&tv[j], *keyptr); j++;
    }
    if (cdb_get_values(cdbsock, tv, j, kp_str) != CONFD_OK) {
      /* key not found in the unlikely event that it was deleted after our
         cdb_index() check */
      confd_data_reply_next_key(tctx, NULL, -1, -1);
      return CONFD_OK;
    }
    for (i = 0; i < j; i++) {
      v[i].type = tv[i].v.type;
      v[i].val = tv[i].v.val;
    }
  }
  /* reply */
  confd_data_reply_next_key(tctx, &v[0], j, -1);
  return CONFD_OK;
}

static int find_next_object(struct confd_trans_ctx *tctx,
                            confd_hkeypath_t *keypath,
                            enum confd_find_next_type type,
                            confd_value_t *keys, int nkeys)
{
  int pos = -1, n_list_entries, nobj, i, j, n = 0, real_nkeys = 0;
  int skip_begin_end = 0;
  confd_tag_value_t *tv, *itv;
  struct confd_tag_next_object *tobj;
  struct confd_cs_node *cs_node, *start;
  char kp_str[BUFSIZ], *lastslash, stars[BUFSIZ], *lastprefix, tmpc;
  u_int32_t *keyptr;

  mk_kp_str(&kp_str[0], BUFSIZ, keypath, KP_MOD);
  start = confd_find_cs_node(keypath, keypath->len);
  cs_node = confd_cs_node_cd(NULL, kp_str);
  if (cs_node->info.flags & CS_NODE_IS_LEAF_LIST) {
    confd_value_t v;
    confd_value_t *list;
    int n_list, pos;

    if (cdb_exists(cdbsock, kp_str) != 1) {
      confd_data_reply_next_key(tctx, NULL, -1, -1);
    } else {
      cdb_get(cdbsock, &v, kp_str);
      list = CONFD_GET_LIST(&v);
      n_list = CONFD_GET_LISTSIZE(&v);
      if (nkeys == 0) {
        confd_data_reply_next_object_array(tctx, list, 1, -1);
      } else {
        pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
        if (pos == -1) {
          confd_data_reply_next_key(tctx, NULL, -1, -1);
        } else {
          confd_data_reply_next_object_array(tctx, &list[pos], 1, -1);
        }
      }
      if (n_list > 0) {
        confd_free_value(list);
      }
    }
    return CONFD_OK;
  }
  for (keyptr = cs_node->info.keys; keyptr != NULL && *keyptr != 0; keyptr++) {
    real_nkeys++;
  }
  stars[0] = 0;
  for (i = 0; i < real_nkeys-nkeys; i++) {
    strcat(&stars[0], " *");
  }
  if (nkeys == 0) {
    pos = 0; /* first call */
  } else {
    switch (type) {
    case CONFD_FIND_SAME_OR_NEXT:
      if (real_nkeys - nkeys == 0) {
        if((pos = cdb_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys)) < 0) {
          pos = cdb_next_index(cdbsock, "%s{%*x}", kp_str, nkeys, keys);
        }
      } else {
        pos = cdb_next_index(cdbsock, "%s{%*x%s}", kp_str, nkeys, keys, stars);
      }
      break;
    case CONFD_FIND_NEXT:
      pos = cdb_next_index(cdbsock, "%s{%*x%s}", kp_str, nkeys, keys, stars);
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

  if (pos < 0 || (n_list_entries = cdb_num_instances(cdbsock, kp_str)) <= pos)
  {
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
  itv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * nobj * 2 *
                                     (1 + confd_max_object_size(cs_node)));
  j = 0;
  if (cs_node->info.flags & CS_NODE_IS_LIST && cs_node->parent == NULL) {
    /* list at root, need to do one get_values per list entry */
    for (i = 0; i < nobj; i++) {
      j = traverse_cs_nodes(cs_node->children, &itv[j*i], 0);
      ssize_t bufsz = snprintf(NULL, 0, "%s[%d]", &kp_str[0], INT_MAX);
      char tmp_str[bufsz + 1];
      snprintf(&tmp_str[0], sizeof(tmp_str), "%s[%d]", &kp_str[0], pos+i);
      if (cdb_get_values(cdbsock, &itv[j*i], j, &tmp_str[0]) != CONFD_OK) {
        confd_fatal("cdb_get_values() from path %s failed\n", tmp_str);
      }
    }
    j = j*nobj;
  } else {
    /* generic, more memory but less wall clock time with a single get_values */
    for (i = 0; i < nobj; i++) {
      CONFD_SET_TAG_CDBBEGIN(&itv[j], cs_node->tag, cs_node->ns, pos+i); j++;
      j = traverse_cs_nodes(cs_node->children, &itv[0], j);
      CONFD_SET_TAG_XMLEND(&itv[j], cs_node->tag, cs_node->ns); j++;
    }
    skip_begin_end = 1;

    if((lastprefix = strrstr(kp_str, confd_hash2str(cs_node->tag))) != NULL) {
      tmpc = *lastprefix;
      *lastprefix = 0;
      if((lastslash = strrchr(kp_str, '/')) != NULL) {
        if (lastslash != &kp_str[0]) {
          *lastslash = 0;
        } else {
          *lastprefix = tmpc;
        }
      }
    }
    if (cdb_get_values(cdbsock, &itv[0], j, kp_str) != CONFD_OK) {
      confd_fatal("cdb_get_values() from path %s failed\n", kp_str);
    }
  }

  tobj = malloc(sizeof(struct confd_tag_next_object) * (max_nobjs + 1));
  tv = (confd_tag_value_t *) malloc(sizeof(confd_tag_value_t) * max_nobjs * 2 *
                                    (1 + 1 + confd_max_object_size(cs_node)));

  /* create reply */
  int n_itv = j/nobj;
  int n_tv = 0;
  n = 0;
  for (i = 0; i < nobj; i++) {
    tobj[i].tv = &tv[n_tv];
    if (real_nkeys > 0) {
      /* +1 and -2 to skip begin and end tags for each object */
      n = format_object(tobj[i].tv, &itv[n_itv*i+skip_begin_end],
                        n_itv-(skip_begin_end*2), start);
    } else { /* keyless list - add pseudo key */
      CONFD_SET_TAG_INT64(&(tobj[i].tv)[0], 0, i);
      /* +1 and -2 to skip begin and end tags for each object */
      n = format_object(&(tobj[i].tv)[1], &itv[n_itv*i+skip_begin_end],
                       n_itv-(skip_begin_end*2), start);
      n++;
    }
    n_tv += n;
    tobj[i].n = n;
    tobj[i].next = -1; /* -1 is ok here since we are not implementing get_next*
                          callbacks, else next can be (long)pos+i+1; */
    //print_tag_value_array(tobj[i].tv, n, NULL, 0);
  }
  if (pos + i >= n_list_entries) {
    tobj[i].tv = NULL; /* indicate no more list entries */
    tobj[i].n = 0;
    tobj[i].next = -1;
    i++;
  }

  /* reply */
  confd_data_reply_next_object_tag_value_arrays(tctx, tobj, i, 0);
  free(itv);
  free(tv);
  free(tobj);
  return CONFD_OK;
}

/* Normally, we would write the data to the external DB from the write_start()
   or perpare() callbacks and commit the data from the commit() callback. Since
   we are writing to the ConfD CDB operational datastore it is not possible for
   other northbound clients other than MAAPI and CDB API clients to write or
   read (see tailf:export in the *-state.yang modules) the data we can write
   the data to the CDB operational datastore in the commit callback as we are
   ceritain (enough "nines", see for example the Wikipedia "High Availability"
   article) that our write operations will succeed. */
static int t_commit(struct confd_trans_ctx *tctx)
{
  struct confd_tr_item *item = tctx->accumulated;
  confd_hkeypath_t *keypath;
  char kp_str[BUFSIZ];
  char choice_str[BUFSIZ];
  char tmp_str[BUFSIZ];
  char *scase_str, *ns_str;

  while (item) {
    keypath = item->hkp;
    mk_kp_str(&kp_str[0], BUFSIZ, keypath, KP_MOD);
    switch(item->op) {
    case C_SET_ELEM:
      if (item->val->type == C_XMLTAG) {
        ns_str = confd_hash2str(CONFD_GET_XMLTAG_NS(item->val));
        snprintf(tmp_str, sizeof(tmp_str),"%s%s", ns_str, KP_MOD);
        item->val->val.xmltag.ns = confd_str2hash(&tmp_str[0]);
      } else if (item->val->type == C_IDENTITYREF) {
        ns_str = confd_hash2str(item->val->val.idref.ns);
        snprintf(tmp_str, sizeof(tmp_str),"%s%s", ns_str, KP_MOD);
        item->val->val.idref.ns = confd_str2hash(&tmp_str[0]);
      }
      cdb_set_elem(cdbsock, item->val, &kp_str[0]);
      break;
    case C_CREATE:
      cdb_create(cdbsock, &kp_str[0]);
      break;
    case C_REMOVE:
      cdb_delete(cdbsock, &kp_str[0]);
      break;
    case C_SET_CASE:
      confd_pp_value(tmp_str, BUFSIZ, item->choice);
      ns_str = confd_ns2prefix(CONFD_GET_XMLTAG_NS(item->val));
      snprintf(choice_str, sizeof(choice_str),"%s%s:%s", ns_str, KP_MOD,
               tmp_str);
      scase_str = confd_hash2str(CONFD_GET_XMLTAG(item->val));
      cdb_set_case(cdbsock, &choice_str[0], &scase_str[0], &kp_str[0]);
      break;
    default:
      return CONFD_ERR;
    }
    item = item->next;
  }
  return CONFD_OK;
}

/* We accumulate and write to the operational datastore in the commit phase */
static int set_elem(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath,
                    confd_value_t *newval)
{
  return CONFD_ACCUMULATE;
}

static int create_node(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath)
{
  return CONFD_ACCUMULATE;
}

static int remove_node(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath)
{
  return CONFD_ACCUMULATE;
}

static int move_after(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath,
                       confd_value_t *prevkeys)
{
  /*  Not supported for "config false" data so we can't perform this operation
      on the data in the CDB operational datastore. Demo limitation. */
  return CONFD_OK;
}

/* Implemented to set the case in the operational datastore using
   cdb_set_case(). This allows the get_case() callback to check if a case is
   set using the cdb_get_case() statment. */
static int set_case(struct confd_trans_ctx *tctx,
                    confd_hkeypath_t *kp, confd_value_t *choice,
                    confd_value_t *caseval)
{
  return CONFD_ACCUMULATE;
}

#include <time.h>
#include <sys/time.h>
static void libconfd_logger(int syslogprio, const char *fmt, va_list ap) {
  char buf[BUFSIZ];
  struct timeval curTime;
  gettimeofday(&curTime, NULL);
  int milli = curTime.tv_usec / 1000;

  char tbuf [80];
  strftime(tbuf, 80, "%Y-%m-%d %H:%M:%S", localtime(&curTime.tv_sec));

  char currentTime[84] = "";
  snprintf(currentTime, sizeof(currentTime),"%s:%03d", tbuf, milli);
  snprintf(buf, sizeof(buf), "%s ", currentTime);
  strcat(buf, fmt);
  vfprintf(estream, buf, ap);
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
  char *log_fname = "/dev/null";

  while ((c = getopt(argc, argv, "a:P:i:c:x:l:drts")) != EOF) {
    switch(c) {
    case 'a':
      confd_ip = optarg;
      break;
    case 'P':
      confd_port = atoi(optarg);
      break;
    case 'c':
      callpoint = optarg;
      break;
    case 'x':
      max_nobjs = atoi(optarg);
      break;
    case 'l':
      log_fname = optarg;
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

  if ((estream = fopen(log_fname, "w")) == NULL) {
    fprintf(estream, "couldn't open logfile %s\n", log_fname);
    exit(1);
  }
  confd_user_log_hook = libconfd_logger;

  /* Initialize confd library */
  confd_init("cdb-oper-dp", stderr, debuglevel);

  if (callpoint == NULL )
    confd_fatal("Need a callpoint name, -c \"my-callpoint\"\n");

  addr.sin_addr.s_addr = inet_addr(confd_ip);
  addr.sin_family = AF_INET;
  addr.sin_port = htons(confd_port);

  if (confd_load_schemas((struct sockaddr*)&addr,
                         sizeof (struct sockaddr_in)) != CONFD_OK)
    confd_fatal("Failed to load schemas from confd\n");

  if ((dctx = confd_init_daemon("static-dp")) == NULL)
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
  trans.init = t_init;
  trans.commit = t_commit;

  if (confd_register_trans_cb(dctx, &trans) == CONFD_ERR)
    confd_fatal("Failed to register trans cb\n");

  memset(&data, 0, sizeof (struct confd_data_cbs));
  /* assuming large lists and that the content of
     individual leafs are typically not requested */
  data.exists_optional = exists_optional;
  data.get_case = get_case;
  data.num_instances = num_instances;
  data.get_object = get_object;
  data.find_next = find_next;
  data.find_next_object = find_next_object;

  data.set_elem = set_elem;
  data.create = create_node;
  data.remove = remove_node;
  data.move_after = move_after;
  data.set_case = set_case;

  strcpy(data.callpoint, callpoint);
  if (confd_register_data_cb(dctx, &data) == CONFD_ERR)
    confd_fatal("Failed to register data cb\n");

  /* Using confd.conf /candidate/confirmedCommit/revertByCommit "true" as the
     CDB operational data store, here used as an external DB, does not
     implement checkpointing. Thus, the below checkpoint callbacks will not be
     implemented or registered. */
  /*
  db.add_checkpoint_running = add_checkpoint_running;
  db.del_checkpoint_running = del_checkpoint_running;
  db.activate_checkpoint_running = activate_checkpoint_running;

  if (confd_register_db_cb(dctx, &db) == CONFD_ERR)
    confd_fatal("Failed to register db cb\n");
  */

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
