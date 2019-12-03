#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <signal.h>
#include <sys/poll.h>

#include <sys/types.h>
#include <sys/socket.h>

#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/un.h>

#include <assert.h>

#include <confd.h>
#include <confd_cdb.h>
#include <confd_maapi.h>

#ifndef max
#define max(a, b) ((a) > (b) ? (a) : (b))
#endif

#ifndef MAX_ARGS
#define MAX_ARGS 16
#endif

struct cmdline {
    int lineno;
    int argc;
    char *argv[MAX_ARGS];
    struct cmdline *next;
};

struct script {
    char *source;
    struct cmdline *pgm;
};


/* fallback if schema isn't loaded */
#define MAX_ELEMS_PER_OBJECT 42

static char *progname;
static int debug_trace = 0;
static enum confd_debug_level debug = CONFD_SILENT;
static FILE *debugf = NULL;
static int family, type, protocol;
static struct sockaddr *addr;
static socklen_t addrlen;
static enum cdb_db_type db = CDB_RUNNING;
static int sess_flags = -1;
static int cs = -1;             /* global cdb socket variable */
static int ms = -1;             /* global maapi socket variable */
static enum confd_dbname mdb = CONFD_RUNNING;
static char *muser = NULL;
static char *groups[32]; int ngroups = 0;
static char *mctxt = "system";
static int preserve_session = 1;
static int load_schema = 0;     /* -1 = never load, 0 = not loaded yet,
                                   1 = already loaded  */
static int leaf_iter = 0;       /* If non zero, do diff_iterate on
                                 * leaf-lists as leafs. Deprecated. */

#define SERVER "ConfD"
#define PORT CONFD_PORT
#define IPC_ADDR "CONFD_IPC_ADDR"
#define IPC_PORT "CONFD_IPC_PORT"
#define IPC_EXTADDR "CONFD_IPC_EXTADDR"
#define IPC_EXTSOPATH "CONFD_IPC_EXTSOPATH"

#define OK(E) ok((E), #E, __FUNCTION__, __LINE__, "FAILED")
#define OK_PREF(prefix, E) ok((E), #E, __FUNCTION__, __LINE__, (prefix))

#define CMD_CDB        (1 << 0)
#define CMD_CDB_SESS   (1 << 1)
#define CMD_CDB_SUB    (1 << 2)
#define CMD_MAAPI      (1 << 3)
#define CMD_MAAPI_NOUSER (1 << 4)
#define CMD_MAAPI_NOTRANS (1 << 5)
#define CMD_HA         (1 << 6)
#define CMD_WANT_SCHEMA  (1 << 7)


static int ok(int res, char *expr, const char *func, int line, char *prefix)
{
    if (res == CONFD_EOF) {
        fprintf(stderr, "%s: %s, " SERVER " closed connection (CONFD_EOF), "
                "in function %s, line %d\n", prefix, expr, func, line);
        exit(1);
    }
    if (res == CONFD_ERR) {
        fprintf(stderr, "%s: %s, Error: %s (%d): %s, "
                "in function %s, line %d\n", prefix, expr,
                confd_strerror(confd_errno), confd_errno,
                (confd_errno == CONFD_ERR_OS) ? strerror(errno):
                confd_lasterr(), func, line);
        exit(1);
    }
    return res;
}


void get_daemon_addr(char *addrstr, int port)
{
    static struct sockaddr_in in_addr;
    static struct sockaddr_in6 in6_addr;
    static struct sockaddr_un un_addr;
    char *daemon_addr = "127.0.0.1";
    int daemon_port = PORT;
    char *etmp;

    if (addrstr != NULL) {
        daemon_addr = addrstr;
    } else if ((etmp = getenv(IPC_ADDR)) != NULL) {
        daemon_addr = etmp;
    } else if ((etmp = getenv(IPC_EXTADDR)) != NULL) {
        daemon_addr = etmp;
    }
    if (port != 0) {
        daemon_port = port;
    } else if ((etmp = getenv(IPC_PORT)) != NULL) {
        daemon_port = atoi(etmp);
    }

    memset(&in_addr, '\0', sizeof(in_addr));
    memset(&in6_addr, '\0', sizeof(in6_addr));
    memset(&un_addr, '\0', sizeof(un_addr));
    type = SOCK_STREAM;
    protocol = 0;
    if (inet_pton(AF_INET, daemon_addr, &in_addr.sin_addr) == 1) {
        family = PF_INET;
        in_addr.sin_family = AF_INET;
        in_addr.sin_port = htons(daemon_port);
        addr = (struct sockaddr *)&in_addr;
        addrlen = sizeof(in_addr);
    } else if (inet_pton(AF_INET6, daemon_addr, &in6_addr.sin6_addr) == 1) {
        family = PF_INET6;
        in6_addr.sin6_family = AF_INET6;
        in6_addr.sin6_port = htons(daemon_port);
        addr = (struct sockaddr *)&in6_addr;
        addrlen = sizeof(in6_addr);
    } else {
        family = PF_UNIX;
        un_addr.sun_family = AF_UNIX;
        snprintf(un_addr.sun_path, sizeof(un_addr.sun_path),
                 "%s", daemon_addr);
        addr = (struct sockaddr *)&un_addr;
        addrlen = sizeof(un_addr);
    }
}

int get_socket()
{
        return socket(family, type, protocol);
}

void fatal(char *str)
{
    fprintf(stderr, "%s: fatal: %s\n", progname, str);
    exit(1);
}

static void free_tag_values(confd_tag_value_t *tv, int n)
{
    int i;

    for (i = 0; i < n; i++) {
        confd_free_value(CONFD_GET_TAG_VALUE(&tv[i]));
    }
}

static void print_modifications(confd_tag_value_t *val, int nvals,
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

#define INDENT_SIZE 2
#define INDENT_STR ""
static void print_modifications_xml_pretty(confd_tag_value_t *tval, int nvals, int start_indent)
{
  char value_buf[BUFSIZ], xmlns_buf[BUFSIZ];
  int ns = 0, i, j, nns, indent = start_indent;
  char *tag_str = "";
  struct confd_cs_node root, *pnode = NULL, *node = NULL;
  confd_value_t *val = NULL;
  unsigned int size;
  struct confd_type *ctype = NULL;
  struct confd_nsinfo *nsinfo;
  nns = confd_get_nslist(&nsinfo);

  xmlns_buf[0]='\0';

  for (i=0; i<nvals; i++) {
      tag_str = confd_hash2str(CONFD_GET_TAG_TAG(&tval[i]));

      if (indent == start_indent) {
          node = confd_find_cs_root(CONFD_GET_TAG_NS(&tval[i]));
          root.children = node;
          pnode = &root;
      }

      ns = CONFD_GET_TAG_NS(&tval[i]);
      if (indent == start_indent || pnode->ns != ns) {
          for (j=0; j<nns; j++) {
              if (nsinfo[j].hash == ns) {
                  break;
              }
          }
          snprintf(&xmlns_buf[0], sizeof(xmlns_buf), " xmlns=\"%s\"", nsinfo[j].uri);
      }

      switch (CONFD_GET_TAG_VALUE(&tval[i])->type) {
          // start a container/list entry creation/modification
      case C_XMLBEGIN:
          printf("%*s<%s%s>\n", indent, INDENT_STR, tag_str, &xmlns_buf[0]);
          indent += INDENT_SIZE;
          if (pnode != NULL)
              pnode = confd_find_cs_node_child(pnode, tval[i].tag);
          break;
          // exit from a processing of container/list entry creation/modification
      case C_XMLEND:
          indent -= INDENT_SIZE;
          printf("%*s</%s>\n", indent, INDENT_STR, tag_str);
          if (pnode != NULL)
              pnode = pnode->parent;
          break;
          // deletion of a leaf
      case C_NOEXISTS:
          printf("%*s<%s operation=\"delete\"%s>\n",
                 indent, INDENT_STR, tag_str, &xmlns_buf[0]);
          break;
          // deletion of a list entry / container
      case C_XMLBEGINDEL:
          printf("%*s<%s operation=\"delete\"%s>\n",
                 indent, INDENT_STR, tag_str, &xmlns_buf[0]);
          indent += INDENT_SIZE;
          if (pnode != NULL)
              pnode = confd_find_cs_node_child(pnode, tval[i].tag);
          break;
          // type empty leaf creation
      case C_XMLTAG:
          printf("%*s<%s/%s>\n", indent, INDENT_STR,
                 tag_str, &xmlns_buf[0]);
          break;
      case C_LIST:
          val =  CONFD_GET_LIST(CONFD_GET_TAG_VALUE(&tval[i]));
          size = CONFD_GET_LISTSIZE(CONFD_GET_TAG_VALUE(&tval[i]));
          if (pnode == NULL ||
              (node = confd_find_cs_node_child(pnode, tval[i].tag)) == NULL ||
              (ctype = confd_get_leaf_list_type(node)) == NULL ||
              confd_val2str(ctype, &val[0], value_buf, sizeof(value_buf)) == CONFD_ERR) {
              for (j = 0; j < size; j++) {
                  confd_pp_value(value_buf, sizeof(value_buf), &val[j]);
                  printf("%*s<%s%s>%s</%s>\n", indent,
                         INDENT_STR, tag_str, &xmlns_buf[0], value_buf, tag_str);
              }
          } else {
              for (j = 0; j < size; j++) {
                  if (confd_val2str(ctype, &val[j], value_buf, sizeof(value_buf)) == CONFD_ERR) {
                      confd_pp_value(value_buf, sizeof(value_buf), &val[j]);
                  }
                  printf("%*s<%s%s>%s</%s>\n", indent,
                         INDENT_STR, tag_str, &xmlns_buf[0], value_buf, tag_str);
              }
          }
          break;
          // regular leaf creation/modification
      default:
          if (pnode == NULL ||
              (node = confd_find_cs_node_child(pnode, tval[i].tag)) == NULL ||
              confd_val2str(node->info.type, CONFD_GET_TAG_VALUE(&tval[i]),
                            value_buf, sizeof(value_buf)) == CONFD_ERR) {
              confd_pp_value(value_buf, sizeof(value_buf),
                             CONFD_GET_TAG_VALUE(&tval[i]));
          }
          printf("%*s<%s%s>%s</%s>\n", indent,
                 INDENT_STR, tag_str, &xmlns_buf[0], value_buf, tag_str);
          break;
      }
      xmlns_buf[0]='\0';
  }
  indent -= INDENT_SIZE;
}

static int common_trigger_subscriptions(int sock, int sub_points[], int len)
{
    if (db == CDB_OPERATIONAL)
        return cdb_trigger_oper_subscriptions(sock, sub_points, len,
                                             sess_flags == -1 ? 0 : sess_flags);
    else
        return cdb_trigger_subscriptions(sock, sub_points, len);
}

static int common_subscribe(int sock, int prio, int nspace,
                            int *spoint, char *path)
{
    if (db == CDB_OPERATIONAL)
        return cdb_oper_subscribe(sock, nspace, spoint, path);
    else
        return cdb_subscribe(sock, prio, nspace, spoint, path);
}

static int common_sync_subscription_socket(int sock,
                                           enum cdb_subscription_sync_type st)
{
    return cdb_sync_subscription_socket(sock, db == CDB_OPERATIONAL ?
                                        CDB_DONE_OPERATIONAL : st);
}

static int common_sub_progress(int sock, char *fmt, ...)
{
    va_list args;
    char buf[BUFSIZ];

    if (db == CDB_OPERATIONAL) {
        /* not available */
        return CONFD_OK;
    } else {
        va_start(args, fmt);
        vsnprintf(buf, sizeof(buf), fmt, args);
        va_end(args);
        return cdb_sub_progress(sock, "%s", buf);
    }
}

static void iter_common(confd_hkeypath_t *kp,
                        enum cdb_iter_op op,
                        confd_value_t *oldv,
                        confd_value_t *newv,
                        void *state)
{
    char tmppath[BUFSIZ];
    char tmpbuf1[BUFSIZ], tmpbuf2[BUFSIZ];
    char *opstr = "";
    char *subpath = (char *)state;
    struct confd_cs_node *tnode = confd_find_cs_node(kp, kp->len);
    confd_pp_kpath(tmppath, BUFSIZ, kp);

#define PPV(VP, BUF)                                                    \
    {                                                                   \
        if ((tnode == NULL) ||                                          \
            (confd_val2str(tnode->info.type, VP, BUF,                   \
                           sizeof(BUF)/sizeof(*BUF)) == CONFD_ERR)) {   \
            confd_pp_value(BUF, sizeof(BUF)/sizeof(*BUF), VP);          \
        }                                                               \
    }

    switch (op) {
    case MOP_CREATED:      opstr = "created";  break;
    case MOP_DELETED:      opstr = "deleted";  break;
    case MOP_VALUE_SET:    opstr = "set";      break;
    case MOP_MODIFIED:     opstr = "modified"; break;
    case MOP_MOVED_AFTER:  opstr = "moved";    break;
    case MOP_ATTR_SET:     fatal("got MOP_ATTR_SET in cdb_diff_iterate()");
    }

    tmpbuf1[0] = tmpbuf2[0] = '\0';
    if (oldv) { PPV(oldv, tmpbuf1); }
    if (op != MOP_MOVED_AFTER) {
        if (newv) { PPV(newv, tmpbuf2); }
    } else {
        if (newv) {
            char *p = tmpbuf2;
            confd_value_t *vp = newv;
            if (tnode != NULL)
                tnode = tnode->children;
            while (vp->type != C_NOEXISTS && p - tmpbuf2 < BUFSIZ) {
                if (p == tmpbuf2) {
                    p += snprintf(p, BUFSIZ, "after {");
                } else {
                    p += snprintf(p, BUFSIZ - (p - tmpbuf2), " ");
                }
                {
                    int c = 0;
                    int sz = BUFSIZ - (p - tmpbuf2);

                    if ((tnode == NULL) ||
                        ((c = confd_val2str(tnode->info.type, vp, p, sz)) ==
                         CONFD_ERR)) {
                        c = confd_pp_value(p, sz, vp);
                    }
                    p += c;
                }
                if (tnode != NULL)
                    tnode = tnode->next;
                vp++;
            }
            if (p - tmpbuf2 < BUFSIZ)
                snprintf(p, BUFSIZ - (p - tmpbuf2), "}");
        } else {
            snprintf(tmpbuf2, BUFSIZ, "first");
        }
    }

#undef PPV

    common_sub_progress(cs, "  diff_iterate: %s %s %s (%s -> %s)",
                        subpath, tmppath, opstr, tmpbuf1, tmpbuf2);

    if (oldv || newv) {
        printf("%s %s %s (%s -> %s)\n",
               subpath, tmppath, opstr, tmpbuf1, tmpbuf2);
    } else {
        printf("%s %s %s\n", subpath, tmppath, opstr);
    }
}


static enum cdb_iter_ret subwait_iter(confd_hkeypath_t *kp,
                                      enum cdb_iter_op op,
                                      confd_value_t *oldv,
                                      confd_value_t *newv,
                                      void *state)
{
    iter_common(kp, op, oldv, newv, state);
    return ITER_RECURSE;
}

static enum cdb_iter_ret subwait_iter_m(confd_hkeypath_t *kp,
                                        enum cdb_iter_op op,
                                        confd_value_t *oldv,
                                        confd_value_t *newv,
                                        void *state)
{
    int nvals;
    confd_tag_value_t *val;

    iter_common(kp, op, oldv, newv, state);
    if (kp->v[0][0].type != C_XMLTAG &&
        (op == MOP_CREATED || op == MOP_MODIFIED)) {
        /* a created or modified list entry */
        OK(cdb_get_modifications_iter(cs, CDB_GET_MODS_INCLUDE_LISTS,
                                      &val, &nvals));
        //OK(cdb_get_modifications_iter(cs, 0, &val, &nvals));
        print_modifications(val, nvals, confd_find_cs_node(kp, kp->len), 2);
        free_tag_values(val, nvals);
        free(val);
    }
    return ITER_RECURSE;
}

static enum cdb_iter_ret subwait_citer(confd_hkeypath_t *kp,
                                       enum cdb_iter_op op,
                                       confd_value_t *oldv,
                                       confd_value_t *newv,
                                       char *clistr,
                                       int tc,
                                       struct confd_cli_token *tokens,
                                       void *state)
{
    int i;
    iter_common(kp, op, oldv, newv, state);
    printf("CLI COMMANDS:\n%s\n", clistr);
    for (i=0; i<tc; i++) {
        char b[255];
        confd_pp_value(b, 255, &tokens[i].val);
        printf("token[%d] = \"%s\" \"%s\"\n", i, b, tokens[i].string);
    }
    return ITER_RECURSE;
}

static enum cdb_iter_ret subwait_citer2(confd_hkeypath_t *kp,
                                       enum cdb_iter_op op,
                                       confd_value_t *oldv,
                                       confd_value_t *newv,
                                       char *clistr,
                                       int tc,
                                       struct confd_cli_token *tokens,
                                       void *state)
{
    int i;
    printf("%s", clistr);
    for (i=0; i<tc; i++) {
        char b[255];
        confd_pp_value(b, 255, &tokens[i].val);
        printf("token[%d] = \"%s\" \"%s\"\n", i, b, tokens[i].string);
    }
    return ITER_RECURSE;
}

static void do_subwait_mods(char *argv[])
                      /* <path> [prio] [loop] [modpath] ['suppress_defaults'] */
{
    int id, n, i, prio, loop, subids[1];
    int flags = CDB_GET_MODS_INCLUDE_LISTS;
    const char *mp = NULL;
    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    if (argv[1] && argv[2] && argv[3]) {
        mp = argv[3];
    } else {
        mp = argv[0];
    }
    if (argv[1] && argv[2] && argv[3] && argv[4] &&
        strcmp(argv[4], "suppress_defaults") == 0) {
        flags |= CDB_GET_MODS_SUPPRESS_DEFAULTS;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[0]));
    OK(cdb_subscribe_done(cs));
    printf("SUBSCRIBED TO %s\n", argv[0]);
    for (i=0; i<loop; i++) {
        OK(cdb_read_subscription_socket(cs, subids, &n));
        printf("COMMIT\n");
        {
            int nvals;
            confd_tag_value_t *val;

            OK(cdb_get_modifications(cs, id, flags, &val, &nvals, mp));
            if (strcmp(mp, "/") == 0)
                print_modifications(val, nvals, NULL, 0);
            else
                print_modifications(val, nvals, confd_cs_node_cd(NULL, mp), 0);
            free_tag_values(val, nvals);
            free(val);
        }
        common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
        printf("DONE\n");
        fflush(stdout);
    }
}

#include <pthread.h>
static int nvals;
static confd_tag_value_t *val;
static int flags = CDB_GET_MODS_INCLUDE_LISTS;

void *run_get_mods( void *id ) {
  OK(cdb_get_modifications(cs, *((int *)id), flags, &val, &nvals, NULL));
  return NULL;
}

static void do_subwait_mods_xml(char *argv[])
                      /* <path> [prio] [loop] ['suppress_defaults'] */
{
    int id, n, i, prio, loop, subids[1];
    //int flags = CDB_GET_MODS_INCLUDE_LISTS;
    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    if (argv[1] && argv[2] && argv[3] &&
        strcmp(argv[3], "suppress_defaults") == 0) {
        flags |= CDB_GET_MODS_SUPPRESS_DEFAULTS;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[0]));
    fprintf(stderr, "SUBSCRIBED TO CONFD CONFIG CHANGES UNDER %s SUBID %d\n", argv[0], id);
    OK(cdb_subscribe_done(cs));
    for (i=0; i<loop; i++) {
        OK(cdb_read_subscription_socket(cs, subids, &n));
        printf("CONFD CONFIG CHANGE NOTIFICATION\n");
        {
            pthread_t thread;

            if (pthread_create(&thread, NULL, run_get_mods, (void *)&id) != 0) {
                fprintf(stderr, "Failed to create thread\n");
            }
            sleep(5);
            printf("SYNC SUBSCRIPTION WITH CONFD\n");
            common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
            printf("PRINT CHANGES RECEIVED FROM CONFD\n");
            pthread_join(thread, NULL);
            printf("<config xmlns=\"http://tail-f.com/ns/config/1.0\">\n");
            print_modifications_xml_pretty(val, nvals, 2);
            printf("</config>\n");
            fflush(stdout);
            free_tag_values(val, nvals);
            free(val);
        }
        fprintf(stderr,"DONE PRINTING CHANGES RECEIVED FROM CONFD\n");
    }
}

static void do_subwait_dimods(char *argv[]) /* <path> [prio] [loop] */
{
    int id, n, i, prio, loop, subids[1];
    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[0]));
    OK(cdb_subscribe_done(cs));
    //fprintf(stderr, "SUBSCRIBED TO %s\n", argv[0]);
    for (i=0; i<loop; i++) {
        OK(cdb_read_subscription_socket(cs, subids, &n));
        //printf("COMMIT\n");
        OK(cdb_diff_iterate(cs, id, subwait_iter_m,
                            leaf_iter|ITER_WANT_PREV|ITER_WANT_ANCESTOR_DELETE,
                            argv[0]));
        common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
        //printf("DONE\n");
        fflush(stdout);
    }
}

/* Two-phase subscription */
static void do_subwait_iter2p(char *argv[]) /* <path> [prio] [loop] */
{
    int id, i, prio, loop;
    enum cdb_sub_type type;

    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    /* we don't have (and won't get) two-phase oper subscriptions, but we may
       use this command with '-o' for the cdb_read_subscription_socket2() */
    type = db == CDB_OPERATIONAL ?
        CDB_SUB_OPERATIONAL : CDB_SUB_RUNNING_TWOPHASE;
    OK(cdb_subscribe2(cs, type, 0, prio, &id, 0, argv[0]));
    OK(cdb_subscribe_done(cs));
    printf("SUBSCRIBED TO %s\n", argv[0]);
    for (i=0; i<loop; i++) {
        int flags, len, *subids;
        enum cdb_sub_notification type;
        OK(cdb_read_subscription_socket2(cs, &type, &flags, &subids, &len));
        switch (type) {
        case CDB_SUB_PREPARE: printf("PREPARE"); break;
        case CDB_SUB_COMMIT:  printf("COMMIT");  break;
        case CDB_SUB_ABORT:   printf("ABORT");   break;
        case CDB_SUB_OPER:    printf("OPER");    break;
        }
        if (flags & CDB_SUB_FLAG_TRIGGER) { printf(" (trigger)"); }
        if (flags & CDB_SUB_FLAG_REVERT)  { printf(" (revert)"); }
        if (flags & CDB_SUB_FLAG_IS_LAST) { printf(" (last)"); }
        if (flags & CDB_SUB_FLAG_HA_IS_SLAVE) { printf(" (slave)"); }
        printf("\n");
        if ((type == CDB_SUB_PREPARE) || (type == CDB_SUB_COMMIT)) {
            common_sub_progress(cs, "going into diff_iterate on id %d", id);
            OK(cdb_diff_iterate(cs, id, subwait_iter,
                                leaf_iter
                                | ITER_WANT_PREV
                                | ITER_WANT_ANCESTOR_DELETE,
                                argv[0]));
            common_sub_progress(cs, "cdb_diff_iterate(%d) done.", id);
        }
        free(subids);
        common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
        printf("DONE\n");
        fflush(stdout);
    }
}

/* Two-phase subscription */
static void do_subwait_abort2p(char *argv[]) /* <path> [prio] [loop] */
{
    int id, i, prio, loop;
    enum cdb_sub_type type;

    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    /* we don't have (and won't get) two-phase oper subscriptions, but we may
       use this command with '-o' for the cdb_read_subscription_socket2() */
    type = db == CDB_OPERATIONAL ?
        CDB_SUB_OPERATIONAL : CDB_SUB_RUNNING_TWOPHASE;
    OK(cdb_subscribe2(cs, type, 0, prio, &id, 0, argv[0]));
    OK(cdb_subscribe_done(cs));
    printf("SUBSCRIBED TO %s\n", argv[0]);
    for (i=0; i<loop; i++) {
        int flags, len, *subids;
        enum cdb_sub_notification type;
        OK(cdb_read_subscription_socket2(cs, &type, &flags, &subids, &len));
        switch (type) {
        case CDB_SUB_PREPARE: printf("PREPARE"); break;
        case CDB_SUB_COMMIT:  printf("COMMIT");  break;
        case CDB_SUB_ABORT:   printf("ABORT");   break;
        case CDB_SUB_OPER:    printf("OPER");    break;
        }
        if (flags & CDB_SUB_FLAG_TRIGGER) { printf(" (trigger)"); }
        if (flags & CDB_SUB_FLAG_REVERT)  { printf(" (revert)"); }
        if (flags & CDB_SUB_FLAG_IS_LAST) { printf(" (last)"); }
        if (flags & CDB_SUB_FLAG_HA_IS_SLAVE) { printf(" (slave)"); }
        printf("\n");
        if (type == CDB_SUB_PREPARE) {
            cdb_sub_abort_trans(cs, CONFD_ERRCODE_RESOURCE_DENIED,
                                      0, 0, "AN ARTIFICIAL ABORT OF THE TRANSACTION");
        }
        free(subids);
        common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
        printf("DONE\n");
        fflush(stdout);
    }
}

/* Wait for a path to change */
static void do_subwait_citer(char *argv[]) /* <path> [prio] [loop] */
{
    int id, n, i, prio, loop, subids[1];
    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[0]));
    OK(cdb_subscribe_done(cs));
    printf("SUBSCRIBED TO %s\n", argv[0]);
    for (i=0; i<loop; i++) {
        OK(cdb_read_subscription_socket(cs, subids, &n));
        printf("COMMIT\n");
        common_sub_progress(cs, "going into diff_iterate on id %d", id);
        cdb_cli_diff_iterate(cs, id, subwait_citer,
                             leaf_iter|ITER_WANT_PREV|ITER_WANT_ANCESTOR_DELETE,
                             argv[0]);
        common_sub_progress(cs, "cdb_diff_iterate(%d) done.", id);
        common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
        printf("DONE\n");
        fflush(stdout);
    }
}

/* Wait for a path to change */
static void do_subwait_citer2(char *argv[]) /* <path> [prio] [loop] */
{
    int id, n, i, prio, loop, subids[1];
    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    if (argv[1] && argv[2]) {
        loop = atoi(argv[2]);
        if (loop == 0) loop = 1;
    } else {
        loop = 1;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[0]));
    OK(cdb_subscribe_done(cs));
    printf("SUBSCRIBED TO %s\n", argv[0]);
    for (i=0; i<loop; i++) {
        OK(cdb_read_subscription_socket(cs, subids, &n));
        printf("COMMIT\n");
        common_sub_progress(cs, "going into diff_iterate on id %d", id);
        cdb_cli_diff_iterate(cs, id, subwait_citer2,
                             leaf_iter|ITER_WANT_PREV|ITER_WANT_ANCESTOR_DELETE,
                             argv[0]);
        common_sub_progress(cs, "cdb_diff_iterate(%d) done.", id);
        common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
        printf("DONE\n");
        fflush(stdout);
    }
}

/* Wait for a path to change */
static void do_subwait(char *argv[]) /* <path> [prio] */
{
    int id, n, prio, subids[1];
    if (argv[1]) {
        prio = atoi(argv[1]);
    } else {
        prio = 10;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[0]));
    OK(cdb_subscribe_done(cs));
    OK(cdb_read_subscription_socket(cs, subids, &n));
    printf("%s triggered\n", argv[0]);
    common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
}

/* Wait for a path to change, with a timeout */
static void do_subwait_timeout(char *argv[]) /* <timeout> <path> [prio] */
{
    int id, n, prio, subids[1];
    int timeout = atoi(argv[0]) * 1000;
    struct pollfd fds[1];
    if (argv[2]) {
        prio = atoi(argv[2]);
    } else {
        prio = 10;
    }
    OK(common_subscribe(cs, prio, 0, &id, argv[1]));
    OK(cdb_subscribe_done(cs));
    fds[0].fd = cs; fds[0].events = POLLIN; fds[0].revents = 0;
    if (poll(fds, 1, timeout) <= 0) {
        printf("timeout\n");
        exit(1);
    }
    OK(cdb_read_subscription_socket(cs, subids, &n));
    printf("%s triggered\n", argv[0]);
    common_sync_subscription_socket(cs, CDB_DONE_PRIORITY);
}

static void do_cdb_trigger_subscriptions(char *argv[])
{
    if (argv[0] == NULL) {
        OK(common_trigger_subscriptions(cs, NULL, 0));
    } else {
        int i, subids[MAX_ARGS];
        for (i=0; argv[i] != NULL; i++) {
            subids[i] = atoi(argv[i]);
        }
        OK(common_trigger_subscriptions(cs, subids, i));
    }
}

static struct cmd_t {
    char *cmd;
    char *aliases[4];
    void (*func)(char **);
    int nargs;              /*  N            = exactly N arguments
                               -N            = at least N arguments
                               -(MAX_ARGS-1) = zero or more arguments,*/
#define ZERO_OR_MORE_ARGS (-(MAX_ARGS-1))
    int cmd_flags;
    char *help_args;
    char *help;
} cmds[] = {
    /* CDB subscription */
    {
        "subwait_mods_xml", {"smx",NULL}, do_subwait_mods_xml, -1,
        CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop] ['suppress_defaults']",
        "subscribe to <path>, run cdb_get_modifications() when notified"
        "and print XML"
    },
    {
        "subwait_mods", {"sm",NULL}, do_subwait_mods, -1,
        CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop] [modpath] ['suppress_defaults']",
        "subscribe to <path> and run cdb_get_modifications() when notified"
    },
    {
        "subwait_mods_iter", {"smi",NULL},
        do_subwait_dimods, -1, CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop]",
        "subscribe to <path> and run cdb_diff_iterate() (and "
        "cdb_get_modifications_iter() on created/modified list entries) "
        "when notified"
    },
    {
        "subwait_iter2", {NULL}, do_subwait_iter2p, -1,
        CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop]",
        "subscribe to <path> using two phase subscription "
        "and run cdb_diff_iterate() when notified"
    },
    {
        "subwait_abort2", {NULL}, do_subwait_abort2p, -1,
        CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop]",
        "subscribe to <path> using a two phase subscription "
        "and abort the transaction when notified"
    },
    {
        "subwait_cli_iter", {NULL}, do_subwait_citer, -1,
        CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop]", NULL
    },
    {
        "cli_sub", {NULL}, do_subwait_citer2, -1,
        CMD_CDB|CMD_CDB_SUB|CMD_WANT_SCHEMA,
        "<path> [priority] [loop]", NULL
    },
    {
        "subwait", {"w",NULL}, do_subwait, -1, CMD_CDB|CMD_CDB_SUB,
        "<path> [priority]", NULL
    },
    {
        "subto", {NULL}, do_subwait_timeout, -2, CMD_CDB|CMD_CDB_SUB,
        "<timeout> <path> [priority]", NULL
    },
    {
        "trigger_subscriptions", {"trigger", NULL},
        do_cdb_trigger_subscriptions, ZERO_OR_MORE_ARGS, CMD_CDB,
        "[subid]...", "Trigger all, or specified, CDB subscriptions"
    },

    { NULL, {NULL}, NULL, 0, 0, NULL, NULL }
};

static void free_script(struct script *pgm)
{
    if (pgm) {
        struct cmdline *p, *pnext;
        for (p=pgm->pgm; p; p=pnext) {
            int i;
            for (i=0; i<p->argc; i++) {
                free(p->argv[i]);
            }
            pnext = p->next;
            free(p);
        }
        free(pgm);
    }
}

static int run(struct script *pgm, int do_close)
{
    struct cmdline *pc;

    for (pc=pgm->pgm; pc; pc=pc->next) {
        char *cmd = pc->argv[0];
        int argc = pc->argc - 1;
        struct cmd_t *cc;
        if (pc->argc == 0) continue;

        for (cc = cmds; cc->cmd != NULL; cc++) {
            if (strcmp(cmd, cc->cmd) == 0) {
                break;
            }
            if (cc->aliases[0]) {
                char **alias;
                for (alias = cc->aliases; *alias != NULL; alias++) {
                    if (strcmp(cmd, *alias) == 0) {
                        break;
                    }
                }
                if (*alias) {
                    break;
                }
            }
        }
        if (cc->cmd) {
            if (debug_trace) {
                int i;
                fprintf(debugf, "+%s", cc->cmd);
                for (i=1; i<pc->argc; i++) {
                    fprintf(debugf, " \"%s\"", pc->argv[i]);
                }
                fprintf(stderr, "\n");
            }
            if ((cc->nargs != ZERO_OR_MORE_ARGS) && (argc < abs(cc->nargs))) {
                fprintf(debugf, "too few arguments to cmd: %s\n", cc->cmd);
                fatal("too few arguments");
            }
            if ((cc->cmd_flags & CMD_WANT_SCHEMA) && (load_schema == 0)) {
                OK(confd_load_schemas(addr, addrlen));
                load_schema = 1;
            }
            if ((cc->cmd_flags & CMD_CDB) && (cs < 0)) {
                enum cdb_sock_type st = (cc->cmd_flags & CMD_CDB_SUB) ?
                    CDB_SUBSCRIPTION_SOCKET : CDB_DATA_SOCKET;
                assert((cs = get_socket()) >= 0);
                OK(cdb_connect(cs, st, addr, addrlen));
            }
            if (cc->cmd_flags & CMD_MAAPI) {
                /* start user session */
                if (ms < 0) {
                    struct confd_ip msrc;
                    msrc.af = AF_INET;
                    inet_pton(AF_INET, "127.0.0.1", &msrc.ip.v4);
                    assert((ms = get_socket()) >= 0);
                    OK(maapi_connect(ms, addr, addrlen));
                    if (!(cc->cmd_flags & CMD_MAAPI_NOUSER)) {
                        OK(maapi_start_user_session(
                               ms, muser, mctxt,
                               (const char **)groups, ngroups,
                               &msrc, CONFD_PROTO_TCP));
                    }
                }
            }
            cc->func(pc->argv + 1);
            if (!preserve_session && (cs >= 0)) {
                if (cc->cmd_flags & CMD_CDB_SESS) { OK(cdb_end_session(cs)); }
                OK(cdb_close(cs));
                cs = -1;
            }
        } else {
            fprintf(stderr, "%s:%d: unknown command: %s (try "
                    "\"%s -h commands\" for a list of avaliable commands)\n",
                    pgm->source, pc->lineno, cmd, progname);
            fatal("unknown command");
        }
    }
    return 0;
}

static void print_script(struct script *program, FILE *f)
{
    struct cmdline *c, *prev = NULL;
    int line=1, i;
    for (c=program->pgm; c != NULL; prev=c, c=c->next) {
        for (; line < c->lineno; line++) { fprintf(f, "\n"); }
        if (prev && (prev->lineno == c->lineno)) {
            fprintf(f, " ; ");
        }
        if (c->argc > 0) {
            fprintf(f, "%s", c->argv[0]);
            for (i=1; i < c->argc; i++) {
                fprintf(f, " \"%s\"", c->argv[i]);
            }
        }
    }
    fprintf(f, "\n");
}

static struct cmdline *read_line(int lineno, char *line)
{
    struct cmdline *l;
    char *b, *c;
    int inquote;

    b = line;
    while(isspace(*b)) b++;
    if ((*b == 0) || (*b == '#')) {
        /* empty line */
        return NULL;
    }

    l = (struct cmdline *)malloc(sizeof(struct cmdline));
    assert(l);
    memset(l, 0, sizeof(*l));
    l->lineno = lineno;
    l->argc = 0;
    l->next = NULL;

    for (;;b=c) {
        char *argtmp; size_t argsz;
        inquote = 0;
        while(isspace(*b)) b++;
        if ((*b == 0) || (*b == '#')) goto done;
        if (*b == ';') {
            l->next = read_line(lineno, b+1);
            goto done;
        }
        if (*b == '"') {
            b++;
            inquote=1;
        }
        for (c=b;;c++) {
            if (*c == 0) break;
            if (!inquote && isspace(*c)) break;
            if (!inquote && (*c == '#')) break;
            if (!inquote && (*c == ';')) break;
            if (inquote && (*c == '"')) break;
        }
        argsz = c-b+1;
        argtmp = (char *)malloc(argsz);
        assert(argtmp);
        memset(argtmp, 0, argsz);
        memcpy(argtmp, b, argsz-1);
        if (l->argc == MAX_ARGS) {
            fprintf(stderr, "%d: MAX_ARGS reached: %s\n", lineno, argtmp);
            exit(1);
        }
        l->argv[l->argc] = argtmp;
        l->argc++;
        if (inquote) c++;
    }
    done:
    return l;
}

static struct script *read_file(char *filename)
{
    FILE *f;
    char line[BUFSIZ];
    struct cmdline *cur;
    struct script *program;
    int lineno;

    program = (struct script *)malloc(sizeof(struct script));
    assert(program);

    if (strcmp(filename, "-") == 0) {
        f = stdin;
        program->source = "stdin";
    } else {
        if ((f = fopen(filename, "r")) == NULL) {
            fprintf(stderr, "Couldn't open \"%s\": %s\n",
                    filename, strerror(errno));
            exit(1);
        }
        program->source = filename;
    }
    program->pgm = NULL;
    for (cur = NULL, lineno = 1; !feof(f); lineno++) {
        struct cmdline *tmp;
        if (fgets(line, BUFSIZ, f) == NULL) break;
        tmp = read_line(lineno, line);
        if (program->pgm == NULL) {
            program->pgm = cur = tmp;
        } else {
            cur->next = tmp;
        }
        while (cur && cur->next) { cur = cur->next; }
    }
    return program;
}

/* fork, listen, child suspends itself */
static void do_listen(int port)
{
    pid_t pid;
    struct sockaddr_in myname;
    int lsock;
    int lineno = 1;
    int on = 1;
    struct script *program;

    lsock = socket(AF_INET, SOCK_STREAM, 0);
    memset(&myname, 0, sizeof(myname));
    myname.sin_family = AF_INET;
    myname.sin_port = htons(port);
    myname.sin_addr.s_addr = inet_addr("127.0.0.1");

    setsockopt(lsock, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));

    if (bind(lsock, (struct sockaddr*)&myname, sizeof(myname) ) < 0 ) {
        fprintf(stderr, "network server bind failure %d\n", errno);
        exit(1);
    }
    listen(lsock, 5);

    if ((pid = fork()) == 0) {
        /* child */

        static struct confd_daemon_ctx *dctx;
        static int ctlsock;

        close(fileno(stdout)); /* make sure shell doesn't wait for output */

        /* create a control socket to ConfD so we can terminate if
           ConfD dies */
        if ((dctx = confd_init_daemon("confd_cmd_daemon")) == NULL)
            confd_fatal("Failed to initialize daemon\n");
        if ((ctlsock = get_socket()) < 0)
            confd_fatal("Failed to open ctlsocket\n");
        if (confd_connect(dctx, ctlsock, CONTROL_SOCKET, addr, addrlen) < 0)
            confd_fatal("Failed to confd_connect() to confd \n");

        while (1) {
            struct pollfd set[2];

            set[0].fd = lsock;
            set[0].events = POLLIN;
            set[0].revents = 0;

            set[1].fd = ctlsock;
            set[1].events = POLLIN;
            set[1].revents = 0;

            if (poll(&set[0], 2, -1) < 0) {
                perror("Poll failed:");
                continue;
            }

            if (set[1].revents & POLLIN) {
                // ConfD died - terminate
                exit(1);
            }
            if (set[0].revents & POLLIN) { // someone is connecting to us
                int asock = accept(lsock, 0,  0);
                char buf[BUFSIZ];
                char *p = &buf[0];
                int more = 1;
                int sz = BUFSIZ-1;
                int r;
                // read one line
                while (more && sz) {
                    if ((r = read(asock, p, sz)) <= 0) {
                        fprintf(stderr, "bad ctl read");
                        exit(1);
                    }
                    p[r] = '\0';
                    if (strchr(p, '\n')) {
                        more = 0;
                    }
                    p += r;
                    sz -= r;
                }

                program = (struct script *)malloc(sizeof(struct script));
                assert(program);
                program->source = "socket";
                program->pgm = read_line(lineno, buf);
                // execute the line
                if (debug > CONFD_SILENT) {
                    print_script(program, stderr);
                }
                run(program, 0);
                free_script(program);
                // close the socket to the client
                close(asock);
                lineno++;
            }
        }


        exit(0);
    }
    printf("%ld\n", (long)pid);
}


static void usage()
{
    printf("Usage:\n"
           "  %s [options] [filename]\n"
           "  %s [options] -c <script>\n"
           "  %s -h | -h commands | -h <command-name>\n",
           progname, progname, progname);
    printf(
        "A utility that provides a command line interface towards some cdb\n"
        "and maapi functions. Commands are expected in filename (or stdin\n"
        "if not provided). Commands can also be given using the -c option.\n"
        "Valid options are:\n");
    printf(
"  -d             Increase debug level for each -d flag\n"
"  -a <address>   Connect to " SERVER " at <address> (default 127.0.0.1)\n"
"  -p <port>      Connect to " SERVER " at <port> (default %d)\n"
"  -r             Commands work on 'running' database\n"
"  -S             Commands work on 'startup' database\n"
"  -o             CDB commands work on CDB operational database\n"
"  -e             MAAPI commands work on candidate database\n"
"  -f [w][p][r|s] Use cdb_start_session2() to start the CDB session - values\n"
"                 w/p/r/s set the CDB_LOCK_WAIT/PARTIAL/REQUEST/SESSION flags\n"
"  -u <user>      Connect to maapi as <user>\n"
"  -g <group>     Connect to maapi with group <group> (more than one allowed)\n"
"  -x <ctxt>      Connect to maapi with context <ctxt> (default system)\n"
"  -s             Perform each command in a different session\n"
"  -c <string>    Commands are read from <string> instead of a file\n"
"  -m             Don't call confd_load_schemas()\n"
"  -U             Make all output unbuffered\n"
"  -L             diff_iterate on leaf-lists as leaf, not list [deprecated]\n"
"  -h             Display this text and exit\n"
"  -h <cmd-name>  Show help for <cmd-name> and exit\n"
"  -h commands    List all available commands and exit\n",
CONFD_PORT);
}

static void help(int argc, char *argv[])
{
    struct cmd_t *cc;

    if (argc == 0) {
        printf("%s: available commands:\n", progname);
    } else {
        int i;
        printf("%s: help for command%s: ", progname, (argc>1) ? "s" : "");
        for(i=0; i<argc; i++) { printf("%s", argv[i]); }
        printf("\n\n");
    }
    for (cc = cmds; cc->cmd != NULL; cc++) {
        if (argc > 0) {
            char **as;
            int i, found = 0;
            for (i=0; i<argc; i++) {
                if (strcmp(argv[i], cc->cmd) == 0) { found++; }
                for (as = cc->aliases; *as != NULL; as++) {
                    if (strcmp(argv[i], *as) == 0) { found++; }
                }
            }
            if (!found) {
                continue;
            }
        }
        printf("%s", cc->cmd);
        if (cc->aliases[0]) {
            char **alias;
            for (alias = cc->aliases; *alias != NULL; alias++) {
                printf("|%s", *alias);
            }
        }
        if (cc->nargs != 0) {
            if (cc->help_args) {
                printf(" %s", cc->help_args);
            } else {
                printf(" (%s%d arguments)",
                       ((cc->nargs < 0) ? "at least " : ""),
                       (cc->nargs == ZERO_OR_MORE_ARGS) ?
                       0 : abs(cc->nargs));
            }
        }
        printf("\n");
        if (cc->help) { printf("  %s\n", cc->help); }
    }
    printf("\n");
}


int main(int argc, char *argv[])
{
    char *confd_addr = NULL;
    int confd_port = 0;
    int need_help = 0;
    int unbuffered_output = 0;
    int c, ecode = 0;
    char *cmd = NULL;
    struct script *pgm = NULL;
    int lport = 0;

    /* Setup progname (without path component) */
    if ((progname = strrchr(argv[0], (int)'/')) == NULL)
        progname = argv[0];
    else
        progname++;

    /* Parse command line */
    while ((c = getopt(argc, argv, "da:p:orSf:isUu:x:g:etc:l:mhL?")) != EOF) {
        switch (c) {
        case 'd':
            debug++;
            break;
        case 't':
            debug_trace++;
            break;
        case 'a':
            confd_addr = optarg;
            break;
        case 'p':
            confd_port = atoi(optarg);
            break;
        case 'r':
            db = CDB_RUNNING;
            mdb = CONFD_RUNNING;
            break;
        case 'o':
            db = CDB_OPERATIONAL;
            mdb = CONFD_OPERATIONAL;
            break;
        case 'S':
            db = CDB_STARTUP;
            mdb = CONFD_STARTUP;
            break;
        case 'e':
            mdb = CONFD_CANDIDATE;
            break;
        case 'f':
            sess_flags = 0;
            if (strchr(optarg, 'w')) sess_flags |= CDB_LOCK_WAIT;
            if (strchr(optarg, 'r')) sess_flags |= CDB_LOCK_REQUEST;
            if (strchr(optarg, 's')) sess_flags |= CDB_LOCK_SESSION;
            if (strchr(optarg, 'p')) sess_flags |= CDB_LOCK_PARTIAL;
            break;
        case 'u':
            muser = optarg;
            break;
        case 'x':
            mctxt = optarg;
            break;
        case 'g':
            groups[ngroups] = optarg;
            ngroups++;
            break;
        case 'i':
            printf("%d\n", getpid());
            fflush(stdout);
            break;
        case 's':
            preserve_session = 0;
            break;
        case 'c':
            cmd = optarg;
            break;
        case 'l':
            lport = atoi(optarg);
            break;
        case 'm':
            load_schema = -1;
            break;
        case 'U':
            unbuffered_output++;
            break;
        case 'L':
            leaf_iter = ITER_WANT_LEAF_LIST_AS_LEAF;
            break;
        case 'h':
            need_help++;
            break;
        default:
            if (optopt == '?') {
                need_help++;
            } else {
                fprintf(stderr, "%s: unknown option -%c "
                        "(try \"%s -h\" for a list of valid options)\n",
                        progname, (char)optopt, progname);
                exit(1);
            }
            break;
        }
    }
    argc -= optind;
    argv += optind;

    if (need_help) {
        if (argc == 0) {
            usage();
        } else {
            if ((strcmp(argv[0], "commands") == 0) ||
                (strcmp(argv[0], "all") == 0)) {
                help(0, NULL);
            } else {
                help(argc, argv);
            }
        }
        exit(0);
    }

    if ((ngroups == 0) && muser) { /* make sure we are always in a group */
        groups[0] = muser;
        ngroups = 1;
    }

    /* Initialize address to confd daemon */
    get_daemon_addr(confd_addr, confd_port);

    /* always save trace output when testing */
    if ((debug == CONFD_SILENT) && (getenv("TEST_DIR") != NULL)) {
        char fname[255];
        char *suffix = getenv("CONFD_CMD_TRACE_SUFFIX");
        char *mode;
        struct sockaddr_in *in_addr_p = (struct sockaddr_in *)addr;

        if ((family != PF_INET) || (ntohs(in_addr_p->sin_port) == PORT)) {
            snprintf(fname, sizeof(fname), "_tmp_%s", progname);
        } else {
            snprintf(fname, sizeof(fname), "_tmp_%s.%d", progname, confd_port);
        }
        if (suffix) {
            char tmpstr[16];
            if (strcmp(suffix, "pid") == 0) {
                snprintf(tmpstr, sizeof(tmpstr), "%lu",(unsigned long)getpid());
                suffix = tmpstr;
            }
            strncat(fname, suffix, sizeof(fname) - strlen(fname) - 1);
        }
        if (getenv("CONFD_CMD_TRACE_APPEND")) {
            mode = "a";
        } else {
            mode = "w";
        }
        if ((debugf = fopen(fname, mode)) == NULL) {
            fprintf(stderr, "Couldn't open \"%s\": %s\n",
                    fname, strerror(errno));
            exit(1);
        }
        debug = CONFD_TRACE;
    } else {
        debugf = stderr;
    }
    if (unbuffered_output) {
        setvbuf(stdout, NULL, _IONBF, 0);
        setvbuf(debugf, NULL, _IONBF, 0);
    }
    confd_init(progname, debugf, debug);
    signal(SIGPIPE, SIG_DFL);

    if (cmd) {
        pgm = (struct script *)malloc(sizeof(*pgm));
        assert(pgm);
        pgm->source = "cmdline";
        pgm->pgm = read_line(0, cmd);
    } else if (lport) {
        do_listen(lport);
    } else {
        pgm = read_file((argc == 0) ? "-" : argv[0]);
    }
    if (debug > CONFD_SILENT && pgm) { print_script(pgm, debugf); }

    if (pgm && pgm->pgm) { ecode = run(pgm, 1); }

    /* keep valgrind happy */
    free_script(pgm);

    exit(ecode);
}
