#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/poll.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

#include <confd_lib.h>
#include <confd_dp.h>
#include <confd_maapi.h>
#include <confd_cdb.h>

#include "aacluster.h"
#include "routes.h"

/* Simple Active-Active synchronizer demonstration that subscribes to ConfD CDB 
   configuration changes that could be the entire configuration (unlikely),  a subtree 
   in the configuration, or a single leaf. The subsriber take part in changes performed
   in the scope of an ACID transaction and forward those changes to other active ConfDs 
   over MAAPI. ConfD run in one process and the synchronizer in another. No synchronization 
   mechanism other than ConfD transactions are utilized. Joining and leaving 
   a cluster is supported. The focus of the example is consistency + partitioning which 
   means we sacrifice some availability due to taking maapi_lock(s) on the nodes we synch
   to. Study the CAP theorem to find out more on why we need to sacrifice availability if 
   we always want to preserve consistency.
*/

#ifdef DO_DEBUG_LOG
#define DEBUGSTR stderr
#define DEBUG_LOG(format, ...) fprintf(DEBUGSTR, "\n%s:%d: " format "\n", __FILE__, __LINE__ , ##__VA_ARGS__)
#else
#define DEBUG_LOG(format, ...)
#endif

static int subsock_cfg;
static int local_spoint[1] = {-1};
static int aasync_usr = 0;

static int local_nodeid = -1;
static int init_nodeid = -1;

/* Hardcoded config to simplify example */
#define CONFD_IP "127.0.0.1"

#define NUM_LOCK_RETRIES 2

#define ACTIVE_CFG_PATH "/r:active-cfg"
#define AACLUSTER_PATH ACTIVE_CFG_PATH"/a:aacluster"
#define AACLUSTER_INIT_NODE_PATH AACLUSTER_PATH"/a:init-nodeid"
#define AACLUSTER_NODE_PATH AACLUSTER_PATH"/a:node"
#define ROUTES_PATH ACTIVE_CFG_PATH"/r:routes"
#define ROUTE_PATH ROUTES_PATH"/r:route"

#define ENTRIES_PER_REQUEST 100

static char progname[10] = { "aasync000" };
static const char *groups[] = { "admin" };

/* Leafs per list entry */
static int nrvals; /* number of route values per list entry */
static int nnvals; /* number of node values per list entry */

/* Our daemon context as a global variable */
/* as well as the ConfD callback function structs */

static struct confd_daemon_ctx *dctx;
static struct confd_trans_cbs trans;
static struct confd_data_cbs hook;
static struct confd_db_cbs dbcbs;
static int ctlsock;
static int workersock;

#ifdef DO_DEBUG_LOG
static char* enumDBStrings[] = {
  "CONFD_NO_DB",
  "CONFD_CANDIDATE",
  "CONFD_RUNNING",
  "CONFD_STARTUP",
  "CONFD_OPERATIONAL",
  "CONFD_TRANSACTION",   /* trans_in_trans */
  "CONFD_PRE_COMMIT_RUNNING"
};
#endif

struct aanode {
  struct aanode *next; /* For the linked list */
  
  int nodeid;
  struct sockaddr_in addr;
  int maapi_socket;
  int th;
};

static struct aanode *aasync_nodes;
static struct aanode *aasync_local_node;
static struct aanode *aasync_tmp_node;

#define AANODE_JOIN(aanodes, naanode) \
  do {				      \
    (naanode)->next = *(aanodes);     \
    *(aanodes) = (naanode);	      \
  } while(0)

#define AANODE_LEAVE(aanodes, naanode)		\
  do {						\
    if(*(aanodes) == (naanode)) {						\
      *(aanodes) = (*aanodes)->next;						\
    } else for(aasync_tmp_node = *(aanodes); aasync_tmp_node != NULL; aasync_tmp_node = aasync_tmp_node->next) { \
	if(aasync_tmp_node->next != NULL && aasync_tmp_node->next == (naanode)) { \
	  aasync_tmp_node->next = (naanode)->next;				\
	  break;							\
	}								\
      }									\
    (naanode)->next = NULL;						\
  } while(0)

/* Help functions */

static int maapi_socket(int *msock, struct sockaddr_in *addr)
{
  if ((*msock = socket(PF_INET, SOCK_STREAM, 0)) < 0 ) {
    DEBUG_LOG("aasync%d: failed to create socket",local_nodeid);
    return CONFD_ERR;
  }
  if (maapi_connect(*msock, (struct sockaddr*)addr, sizeof (struct sockaddr_in)) < 0) {
    DEBUG_LOG("aasync%d: failed to connect port %d",local_nodeid, addr->sin_port);
    return CONFD_ERR;
  }
  
  return CONFD_OK;
}

static void free_tag_values(confd_tag_value_t *tv, int n)
{
  int i;
  for (i = 0; i < n; i++) {
    confd_free_value(CONFD_GET_TAG_VALUE(&tv[i]));
  }
}

#ifdef DO_DEBUG_LOG
/* copied from confd_cmd.c */
static void print_modifications(confd_tag_value_t *val, int nvals,
                                struct confd_cs_node *start_node,
                                int start_indent)
{
    int i, indent = start_indent;
    struct confd_cs_node root, *pnode = start_node, *node;
    char tmpbuf[BUFSIZ];
    char *tmp;

    DEBUG_LOG("aasync%d: print_modifications", local_nodeid);
    
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
		confd_pp_value(tmpbuf, sizeof(tmpbuf), CONFD_GET_TAG_VALUE(&val[i]));
            }
            tmp = tmpbuf;	    
        }
        DEBUG_LOG("%*s%s %s", indent, "",
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
#endif /* DO_DEBUG_LOG */

typedef enum {CREATE, MODIFY, DELETE} modification_type;

static void handle_aacluster_modifications(confd_tag_value_t *val, int nvals)
{
  int i;
  modification_type mod;
  struct aanode *node;
  int nodeid;
  struct sockaddr_in addr;
  
  memset(&addr, 0, sizeof(struct sockaddr_in));
  nodeid = -1;
  
  for (i=0; i<nvals; i++) {  
    switch (CONFD_GET_TAG_VALUE(&val[i])->type) {
    case C_XMLBEGIN:
      /* Set to 'CREATE' for now, check if id key exists next iteration */
      mod = CREATE;
      break;
    case C_XMLBEGINDEL:
      mod = DELETE;
      break;
    case C_XMLEND:
      /* perform the modifications */
      switch (mod) {
      case CREATE:
	/* create a new node */
	node = (struct aanode *) malloc(sizeof(struct aanode));
	memset(node, 0, sizeof(struct aanode));
	node->nodeid = nodeid;
	node->addr.sin_family = AF_INET;
	node->addr.sin_port = addr.sin_port;
	node->addr.sin_addr.s_addr = addr.sin_addr.s_addr;
	AANODE_JOIN(&aasync_nodes, node);
	DEBUG_LOG("aasync%d: node%d joined", local_nodeid, node->nodeid);
	break;
      case MODIFY:
	/* modify an existing node */
	if(nodeid >= 0)
	  node->nodeid = nodeid;
	if(addr.sin_addr.s_addr > 0)
	  node->addr.sin_addr.s_addr = addr.sin_addr.s_addr;
	if(addr.sin_port > 0)
	  node->addr.sin_port = addr.sin_port;
	DEBUG_LOG("aasync%d: node%d modified", local_nodeid, node->nodeid);
	break;
      case DELETE:
	/* delete a node */
	AANODE_LEAVE(&aasync_nodes, node);
	DEBUG_LOG("aasync%d: node%d left", local_nodeid, node->nodeid);
	free(node);
	break;
      default:
	break;
      }
      break;
    case C_XMLTAG:
      break;
    case C_NOEXISTS:
      break;
    default:
      switch (CONFD_GET_TAG_TAG(&val[i])) {
      case a_nodeid:
	/* Get nodeid key value */
	nodeid = CONFD_GET_INT32(CONFD_GET_TAG_VALUE(&val[i]));
	/* Check if nodeid key exists */
        for(node = aasync_nodes; node != NULL; node = node->next) {
	  if(node->nodeid == nodeid) {
	    break;
	  }
	}
	if (node != NULL) {
	  if(mod == CREATE) {
	    /* Key exists, modify leaf(s) */
	    mod = MODIFY;
	  } /* else mod == DELETE */
	}
	break;
      case a_ip:
	addr.sin_addr = CONFD_GET_IPV4(CONFD_GET_TAG_VALUE(&val[i]));
	break;
      case a_port:
	addr.sin_port = htons(CONFD_GET_UINT16(CONFD_GET_TAG_VALUE(&val[i])));
	break;
      default:
	break;
      }
    }
  }
}

static void start_phase1_aasync(int join)
{
  confd_value_t vals[ENTRIES_PER_REQUEST*nrvals];
  int nobj, i, rsock, ret;
  struct maapi_cursor mc;
  struct cdb_phase phase;
  struct aanode *node, *inode = NULL;
  struct confd_ip ip;
  
  /* aasync1--aasyncX join the cluster by doing an initial sync from the aasync init node */
  if(local_nodeid != init_nodeid) {
    for(node = aasync_nodes; node != NULL; node = node->next) {
      if(node->nodeid == init_nodeid) {
	inode = node;
	break;
      }
    }

    if(node == NULL) {
      confd_fatal("aasync%d: no node with id matching init_nodeid %d", local_nodeid, init_nodeid);
    }

    if(join) {
      /* If we are joining an existing cluster we start a transaction towards the node to initialize from */
      /* Start the maapi session */
      ip.af = inode->addr.sin_family;
      ip.ip.v4 = (struct in_addr) inode->addr.sin_addr;
      if ((ret = maapi_start_user_session(inode->maapi_socket, progname, progname,
					  groups, sizeof(groups) / sizeof(*groups),
					  &ip, CONFD_PROTO_TCP)) != CONFD_OK) {
	confd_fatal("\naasync%d: maapi_start_user session to init node %d failed", local_nodeid, init_nodeid);
      }
      i=0;
      while((ret = maapi_lock(inode->maapi_socket, CONFD_RUNNING)) != CONFD_OK) {
	if(i == NUM_LOCK_RETRIES) {
	  confd_fatal("\naasync%d: maapi_lock to init node %d failed. Aborting transaction...", local_nodeid, init_nodeid);
	}
	i++;
	DEBUG_LOG("aasync%d: maapi_lock to init node %d failed. Retry %d of %d", local_nodeid, init_nodeid, i, NUM_LOCK_RETRIES);
	sleep(1);
      }
      if (((inode->th = maapi_start_trans(inode->maapi_socket, CONFD_RUNNING, CONFD_READ_WRITE))) < 0) {
	confd_fatal("\naasync%d: maapi_start_trans to init node %d failed", local_nodeid, init_nodeid);
      }
    } else {
      /* If we are taking part in a cluster init we attach to the init node's init transaction */
      maapi_attach_init(inode->maapi_socket, &(inode->th));
    }

    maapi_attach_init(aasync_local_node->maapi_socket, &(aasync_local_node->th));

    maapi_delete(aasync_local_node->maapi_socket, aasync_local_node->th, ROUTE_PATH);
    
    maapi_init_cursor(inode->maapi_socket, inode->th, &mc, ROUTE_PATH);
    do {
      nobj = ENTRIES_PER_REQUEST;
      ret = maapi_get_objects(&mc, vals, nrvals, &nobj);
      if (ret >= 0 && nobj > 0) {
	for (i = 0; i < nobj; i++) {
	  maapi_set_object(aasync_local_node->maapi_socket, aasync_local_node->th, &vals[i*nrvals], nrvals, ROUTE_PATH);
	}
	DEBUG_LOG("aasync%d: Replaced local route list entries/objects with objects from aasync%d CDB", local_nodeid, init_nodeid);
      } else if (ret < 0) {
	confd_fatal("get_objects failed");
      } else if (nobj == 0) { /* ret == 0 CDB is empty */
	DEBUG_LOG("aasync%d: no more route list entries/objects", local_nodeid);
      }
    } while (ret >= 0 && mc.n != 0);
    maapi_destroy_cursor(&mc);

    if(join) {
      /* If we are joining an existing cluster we must register our node and get the rest of the cluster nodes */
      int nnodes, nodeid;
      struct in_addr ipaddr;
      /* Get number of nodes in the cluster entries list from the init node */
      if((nnodes = maapi_num_instances(inode->maapi_socket, inode->th, AACLUSTER_NODE_PATH)) < 2)   {
	confd_fatal("\naasync%d: maapi_num_instances < 2. We need our own node configuration and one or more nodes in the cluster we are joining. Failed to initialize active-active synchronizer", local_nodeid);
      }
      DEBUG_LOG("aasync%d: maapi_num_instances from aasync%d CDB nnodes %d", local_nodeid, init_nodeid, nnodes);
      {
	confd_value_t vals[nnodes*nnvals];
	
	maapi_init_cursor(inode->maapi_socket, inode->th, &mc, AACLUSTER_NODE_PATH);
	ret = maapi_get_objects(&mc, vals, nnvals, &nnodes);
	if (ret >= 0 && nnodes > 0) {
	  /* Set cluster node configuration in local CDB */
	  for (i = 0; i < nnodes; i ++) {
	    maapi_set_object(aasync_local_node->maapi_socket, aasync_local_node->th, &vals[i*nnvals], nnvals, AACLUSTER_NODE_PATH);
	  }
	  for (i = 0; i < nnodes*nnvals; i += nnvals) {
	    if((nodeid = CONFD_GET_INT32(&vals[i])) != local_nodeid && nodeid != init_nodeid) {
	      node = (struct aanode * ) malloc(sizeof(struct aanode));
	      memset(node, 0, sizeof(struct aanode));
	      node->nodeid = nodeid;
	      ipaddr = CONFD_GET_IPV4(&vals[i+1]);
	      node->addr.sin_addr.s_addr = ipaddr.s_addr;
	      node->addr.sin_family = AF_INET;
	      node->addr.sin_port = htons(CONFD_GET_UINT16(&vals[i+2]));
	      node->maapi_socket = 0;
	      node->th = 0;
	      AANODE_JOIN(&aasync_nodes, node);
	      DEBUG_LOG("aasync%d: node%d joined", local_nodeid, node->nodeid);
	    }
	  }
	  DEBUG_LOG("aasync%d: Replaced local aacluster node entries/objects and local CDB entries/objects with objects from init node %d CDB", local_nodeid, init_nodeid);
	} else if (ret < 0) {
	  confd_fatal("aasync%d: maapi_get_objects failed", local_nodeid);
	}
	maapi_destroy_cursor(&mc);
	DEBUG_LOG("aasync%d: get objects from aasync%d", local_nodeid, init_nodeid);
	maapi_get_object(aasync_local_node->maapi_socket, aasync_local_node->th, &vals[0], nnvals, AACLUSTER_NODE_PATH"{%d}",local_nodeid);

	DEBUG_LOG("aasync%d: set object to aasync%d", local_nodeid, init_nodeid);
	maapi_set_object(inode->maapi_socket, inode->th, &vals[0], nnvals, AACLUSTER_NODE_PATH);

	if(maapi_validate_trans(inode->maapi_socket, inode->th, 0, 0) != CONFD_OK) {
	  confd_fatal("aasync%d: maapi_validate_trans to node %d failed", local_nodeid, inode->nodeid);
	}
	if(maapi_prepare_trans(inode->maapi_socket, inode->th) != CONFD_OK) {
	  confd_fatal("aasync%d: maapi_prepare_trans to node %d failed", local_nodeid, inode->nodeid);
	}

	for(node = aasync_nodes; node != NULL; node = node->next) {
	  if(node->nodeid != local_nodeid && node->nodeid != init_nodeid) {
	    /* Open up MAAPI sessions other active CDBs */
	    if((ret = maapi_socket(&(node->maapi_socket), &(node->addr))) != CONFD_OK) {
	      confd_fatal("\naasync%d: maapi socket connect to node %d failed", local_nodeid, node->nodeid);
	    }
	    /* Start the maapi session */
	    ip.af = node->addr.sin_family;
	    ip.ip.v4 = (struct in_addr) node->addr.sin_addr;
	    
	    if ((ret = maapi_start_user_session(node->maapi_socket, progname, progname,
						groups, sizeof(groups) / sizeof(*groups),
						&ip, CONFD_PROTO_TCP)) != CONFD_OK) {
	      confd_fatal("\naasync%d: maapi_start_user session to node %d failed", local_nodeid, node->nodeid);
	    }
	    /* Take a northbound API (e.g. NETCONF, REST, ..) write lock on other active CDBs */
	    /* By taking a global write lock we avoid risking deadlock situations by making sure 
	       that there is no other transaction in progress on the other node */
	    i=0;
	    while((ret = maapi_lock(node->maapi_socket, CONFD_RUNNING)) != CONFD_OK) {
	      if(i == NUM_LOCK_RETRIES) {
		confd_fatal("\naasync%d: maapi_lock to node %d failed. Aborting transaction...", local_nodeid, node->nodeid);
	      }
	      i++;
	      DEBUG_LOG("aasync%d: maapi_lock to node %d failed. Retry %d of %d", local_nodeid, node->nodeid, i, NUM_LOCK_RETRIES);
	      sleep(1);
	    }
	    if(((node->th = maapi_start_trans(node->maapi_socket, CONFD_RUNNING, CONFD_READ_WRITE))) < 0) {
	      confd_fatal("aasync%d: maapi_start_trans to node%d failed", local_nodeid, node->nodeid);
	    }
	    maapi_set_object(node->maapi_socket, node->th, &vals[0], nnvals, AACLUSTER_NODE_PATH);

	    if(maapi_validate_trans(node->maapi_socket, node->th, 0, 0) != CONFD_OK) {
	      confd_fatal("aasync%d: maapi_validate_trans to node %d failed", local_nodeid, inode->nodeid);
	    }
	  }
	}
	/* We divide the write + validate and prepare into two steps to minimize the time our nodes synched to is unavailable, the maapi_lock() on 
	   the northbound interfaces will be released by the node itself when validation phase is entered and the transaction lock is taken */
	for(node = aasync_nodes; node != NULL; node = node->next) {
	  if(node->nodeid != local_nodeid && node->nodeid != init_nodeid) {
	    if(maapi_prepare_trans(node->maapi_socket, node->th) != CONFD_OK) {
	      confd_fatal("aasync%d: maapi_prepare_trans to node %d failed", local_nodeid, inode->nodeid);
	    }
	  }
	}

	/* Finish of the registration to all nodes by committing the transaction */
	for(node = aasync_nodes; node != NULL; node = node->next) {
	  if(node->nodeid != local_nodeid) {
	    if (maapi_commit_trans(node->maapi_socket, node->th) != CONFD_OK) {
	      confd_fatal("aasync%d: maapi_commit_trans to node %d failed", local_nodeid, node->nodeid);
	    }
	    if (maapi_finish_trans(node->maapi_socket, node->th) != CONFD_OK) {
	      confd_fatal("aasync%d: maapi_finish_trans to node %d failed", local_nodeid, node->nodeid);
	    }
	  }
	}
      }
    } /* if(join) */
    
    /* Signal aasync init_nodeid that inital sync is done by moving to start phase 1 */
    maapi_start_phase(aasync_local_node->maapi_socket, 1, 1);
  } else {
    /* aasync init node wait for all other aasync nodes to finish startup sync before moving to start phase 1 where all nodes commit the init transaction */
    for(node = aasync_nodes; node != NULL; node = node->next) {
      if(node->nodeid != init_nodeid) {
	if ((rsock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
	  confd_fatal("Failed to open socket");
	if (cdb_connect(rsock, CDB_READ_SOCKET, (struct sockaddr *)&(node->addr),
			sizeof (struct sockaddr_in)) < 0)
	  confd_fatal("Failed to cdb_connect() to aasync%d ", node->nodeid);
	cdb_get_phase(rsock, &phase);
	while(phase.phase != 1) {
	  sleep(1);
	  cdb_get_phase(rsock, &phase);
	  DEBUG_LOG("aasync%d: waiting for node%d to enter start phase 1", local_nodeid, node->nodeid);
	}
	close(rsock);
      }
    }

    maapi_start_phase(aasync_local_node->maapi_socket, 1, 1);
    DEBUG_LOG("aasync init node %d: All nodes now in start phase 1", init_nodeid);
  }
}

static void start_phase2_aasync(int join)
{
  int ret;
  struct aanode *node;
    
  if(local_nodeid != init_nodeid) {
    /* If we are joining an existing cluster we go to start phase 2 */
    if(join) {
      if((ret = maapi_start_phase(aasync_local_node->maapi_socket, 2, 0)) != CONFD_OK) {
	  confd_fatal("\naasync%d: failed to maapi_start_phase 2", local_nodeid);
	}
    } else { /* If we are part of a cluster initialization we wait for the init node to put us into start phase 2 */
      maapi_wait_start(aasync_local_node->maapi_socket, 2);
    }
  } else {
    for(node = aasync_nodes; node != NULL; node = node->next) {
      DEBUG_LOG("aasync init node %d: maapi_start_phase 2 for aasync%d", init_nodeid, node->nodeid);
      if(node->nodeid == init_nodeid) {
	if((ret = maapi_start_phase(node->maapi_socket, 2, 0)) != CONFD_OK) {
	  confd_fatal("\naasync init node %d: failed to maapi_start_phase 2 for aasync%d", init_nodeid, node->nodeid);
	}
      } else {
	if((ret = maapi_start_phase(node->maapi_socket, 2, 1)) != CONFD_OK) {
	  confd_fatal("\naasync init node %d: failed to maapi_start_phase 2 for aasync%d", init_nodeid, node->nodeid);
	}
      }
    }
    DEBUG_LOG("aasync init node %d: All nodes now in start phase 2", init_nodeid);
  }
}

/* Transaction hook callbacks for handling global lock/unlock from other active sync ConfD nodes  */
static int t_init(struct confd_trans_ctx *tctx)
{
  DEBUG_LOG("aasynd%d: t_init()", local_nodeid);
  confd_trans_set_fd(tctx, workersock);
    return CONFD_OK;
}

static int t_lock(struct confd_trans_ctx *sctx)
{
  int ret;

  DEBUG_LOG("aasync%d: t_lock() USER %s", local_nodeid, sctx->uinfo->username);
  /* Check user id to unlock */
  if(strncmp(sctx->uinfo->username, progname, 6) == 0) {
    if((ret = maapi_socket(&(aasync_local_node->maapi_socket), &(aasync_local_node->addr))) != CONFD_OK) {
      DEBUG_LOG("aasync%d: t_lock() maapi socket connect failed", local_nodeid);
    }
    maapi_set_user_session(aasync_local_node->maapi_socket, sctx->uinfo->usid);
    maapi_unlock(aasync_local_node->maapi_socket, CONFD_RUNNING);
  }
  return CONFD_OK;
}

static int t_finish(struct confd_trans_ctx *sctx)
{
  DEBUG_LOG("t_finish()  node%d: USER %s", local_nodeid, sctx->uinfo->username);

  if(strncmp(sctx->uinfo->username, progname, 6) == 0) {
    aasync_usr = 0;
  }
  return CONFD_OK;
}

static int global_lock(struct confd_db_ctx *dbx, enum confd_dbname dbname)
{
  DEBUG_LOG("aasync%d: global_lock() USER %s TAKING GLOBAL WRITE LOCK ON %s", local_nodeid, dbx->uinfo->username, enumDBStrings[dbname]);
  /* Check user id to skip synchronizing changes done by another synchronizing active ConfD */
  if(strncmp(dbx->uinfo->username, progname, 6) == 0 && dbname == CONFD_RUNNING) {
    aasync_usr = 1;
  }
  return CONFD_OK;
}

static int hook_write_all(struct confd_trans_ctx *tctx, confd_hkeypath_t *keypath)
{
  DEBUG_LOG("aasync%d: WRITE_ALL callback invoked", local_nodeid);
  return CONFD_OK;
}

int main(int argc, char *argv[]) {
  int debuglevel = CONFD_TRACE;
  int oc, ret, nvals, *subp, reslen, i, nodeid;
  struct confd_ip ip;
  int nnodes = -1;
  enum cdb_sub_notification type;
  confd_tag_value_t *tvals;
  struct aanode *node;
  int join = 0;
  struct maapi_cursor mc;
  struct in_addr ipaddr;
  struct confd_cs_node *object;

  
  while ((oc = getopt(argc, argv, "qdtpjn:")) != -1) {
    switch (oc) {
    case 'q':
      debuglevel = CONFD_SILENT;
      break;
    case 'd':
      debuglevel = CONFD_DEBUG;
      break;
    case 't':
      debuglevel = CONFD_TRACE;
      break;
    case 'p':
      debuglevel = CONFD_PROTO_TRACE;
      break;
    case 'j':
      join = 1;
      break;
    case 'n':
      local_nodeid = atoi(optarg);
      break;
    default:
      DEBUG_LOG("usage: aasync [-qdtpjn:]");
      exit(1);
    }
  }

  if (local_nodeid == -1)
    confd_fatal("What is our node ID? Node ID required. Failed to initialize active-active synchronizer");
  
  sprintf(&progname[0], "aasync%d", local_nodeid);
  
  /* Init library  */
  confd_init(progname, stderr, debuglevel);

  /* Initialize daemon context */
  if ((dctx = confd_init_daemon(progname)) == NULL)
    confd_fatal("Failed to initialize confd");

  /* Init our active-active node list */
  aasync_nodes = NULL;
  node = (struct aanode * ) malloc(sizeof(struct aanode));
  memset(node, 0, sizeof(struct aanode));
  node->nodeid = local_nodeid;
  node->addr.sin_addr.s_addr = inet_addr(CONFD_IP);
  node->addr.sin_family = AF_INET;
  node->addr.sin_port = htons(CONFD_PORT+10*local_nodeid);
  node->maapi_socket = 0;
  node->th = 0;
  AANODE_JOIN(&aasync_nodes, node);
  aasync_local_node = node;

  /* Attach to init transaction to read node cluster information */
  if((ret = maapi_socket(&(aasync_local_node->maapi_socket), &(aasync_local_node->addr))) != CONFD_OK) {
    confd_fatal("\naasync%d: maapi socket connect at init to node 0 failed", local_nodeid);
  }
  
  maapi_attach_init(aasync_local_node->maapi_socket, &(aasync_local_node->th));

  /* Get node to join cluster through or find out if we are it */
  if((ret = maapi_get_int32_elem(aasync_local_node->maapi_socket, aasync_local_node->th, &init_nodeid, AACLUSTER_INIT_NODE_PATH)) != CONFD_OK) {
    confd_fatal("\naasync%d: maapi_get_int32_elem to get init node failed. Failed to initialize active-active synchronizer", local_nodeid);
  }

  DEBUG_LOG("aasync%d: got init nodeid %d from local CDB", local_nodeid, init_nodeid);
  
  if (init_nodeid == -1)
    confd_fatal("Which node ID do we inialize from? Init node ID required. Failed to initialize active-active synchronizer");
  
  if (confd_load_schemas((struct sockaddr *)&(aasync_local_node->addr),
			 sizeof(struct sockaddr_in)) != CONFD_OK) {
    confd_fatal("Failed to load schemas from confd");
  }

  object = confd_cs_node_cd(NULL,  ROUTE_PATH"{%s}");
  nrvals = confd_max_object_size(object);
  object = confd_cs_node_cd(NULL,  AACLUSTER_NODE_PATH"{%s}");
  nnvals = confd_max_object_size(object);
  DEBUG_LOG("aasync%d: nnvals=%d nrvals=%d", local_nodeid, nnvals, nrvals);
  
  /* Get number of nodes in the cluster entries from init transaction */
  if((nnodes = maapi_num_instances(aasync_local_node->maapi_socket, aasync_local_node->th, AACLUSTER_NODE_PATH)) < 2)   {
    confd_fatal("\naasync%d: maapi_num_instances < 2. We need our own node configuration and one or more nodes in the cluster we are joining. Failed to initialize active-active synchronizer", local_nodeid);
  }

  {
    confd_value_t vals[nnodes*nnvals];
     
    maapi_init_cursor(aasync_local_node->maapi_socket, aasync_local_node->th, &mc, AACLUSTER_NODE_PATH);
    ret = maapi_get_objects(&mc, vals, nnvals, &nnodes);
    if (ret >= 0 && nnodes > 0) {
      for (i = 0; i < nnodes*nnvals; i += nnvals) {
        if((nodeid = CONFD_GET_INT32(&vals[i])) != local_nodeid) {
          node = (struct aanode * ) malloc(sizeof(struct aanode));
	  memset(node, 0, sizeof(struct aanode));
	  node->nodeid = nodeid;
	  ipaddr = CONFD_GET_IPV4(&vals[i+1]);
	  node->addr.sin_addr.s_addr = ipaddr.s_addr;
	  node->addr.sin_family = AF_INET;
	  node->addr.sin_port = htons(CONFD_GET_UINT16(&vals[i+2]));
	  node->maapi_socket = 0;
	  node->th = 0;
	  AANODE_JOIN(&aasync_nodes, node);
	  DEBUG_LOG("aasync%d: node%d joined", local_nodeid, node->nodeid);
        }
      }
      DEBUG_LOG("aasync%d: Replaced local aacluster node entries/objects with objects from local CDB", local_nodeid);
    } else if (ret < 0) {
      confd_fatal("get_objects failed");
    }
    maapi_destroy_cursor(&mc);
  }
  
  /* Open up maapi connections */
  if(local_nodeid == init_nodeid) {
    for(node = aasync_nodes; node != NULL; node = node->next) {
      if(node->nodeid != local_nodeid) {
	if((ret = maapi_socket(&(node->maapi_socket), &(node->addr))) != CONFD_OK) {
	  DEBUG_LOG("aasync%d: maapi socket connect at init to node %d failed", local_nodeid, node->nodeid);
	} 
      }
    }
  } else {
    for(node = aasync_nodes; node != NULL; node = node->next) {
      if(node->nodeid == init_nodeid) {
        break;
      }
    }
    if((ret = maapi_socket(&(node->maapi_socket), &(node->addr))) != CONFD_OK) {
      DEBUG_LOG("aasync%d: maapi socket connect at init to node %d failed", local_nodeid, node->nodeid);
    } 
  }

  start_phase1_aasync(join);
    
  /* Init the CDB subscriber to get notified of any updates to the CDB configuration */
  if ((subsock_cfg = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("aasync%d: Failed to open socket", local_nodeid);
  
  if (cdb_connect(subsock_cfg, CDB_SUBSCRIPTION_SOCKET, (struct sockaddr *)&(aasync_local_node->addr),
		  sizeof (struct sockaddr_in)) < 0)
    confd_fatal("aasync%d: Failed to cdb_connect() to confd ", local_nodeid);

  /* Setup subscription points */
  if ((ret = cdb_subscribe2(subsock_cfg, CDB_SUB_RUNNING_TWOPHASE, 0, 1, &local_spoint[0], 0, ACTIVE_CFG_PATH)) != CONFD_OK)
    confd_fatal("aasync%d: cdb_subscribe routes failed", local_nodeid);
  
  if (cdb_subscribe_done(subsock_cfg) != CONFD_OK)
    confd_fatal("aasync%d: cdb_subscribe_done() failed", local_nodeid);

  /* Setup transaction-hook callpoint callbacks */
  memset(&trans, 0, sizeof (struct confd_trans_cbs));
  trans.init = t_init;
  trans.trans_lock = t_lock;
  trans.finish = t_finish;
  memset(&dbcbs, 0, sizeof (struct confd_db_cbs));
  dbcbs.lock = global_lock;
  memset(&hook, 0, sizeof (struct confd_data_cbs));
  hook.write_all = hook_write_all;
  strcpy(hook.callpoint, "write-hook");
  
  if ((ctlsock = socket(PF_INET, SOCK_STREAM, 0)) < 0 )
    confd_fatal("Failed to open ctlsocket");
  
  if (confd_connect(dctx, ctlsock, CONTROL_SOCKET, (struct sockaddr*)&aasync_local_node->addr,
  		    sizeof (struct sockaddr_in)) != CONFD_OK) {
    confd_fatal("Failed to confd_connect() to confd ");
  }
  if ((workersock = socket(PF_INET, SOCK_STREAM, 0)) < 0 ) {
    confd_fatal("Failed to open workersocket");
  }
  if (confd_connect(dctx, workersock, WORKER_SOCKET,(struct sockaddr*)&aasync_local_node->addr,
                    sizeof (struct sockaddr_in)) < 0) {
    confd_fatal("Failed to confd_connect() to confd ");
  }
  
  if (confd_register_trans_cb(dctx, &trans) != CONFD_OK) {
    confd_fatal("Failed to register trans cb");
  }  
  if (confd_register_data_cb(dctx, &hook) != CONFD_OK) {
    confd_fatal("Failed to register data cb");
  }
  if (confd_register_db_cb(dctx, &dbcbs) != CONFD_OK) {
    confd_fatal("Failed to register database cb");
  }
  if (confd_register_done(dctx) != CONFD_OK) {
    confd_fatal("Failed register done");
  }

  start_phase2_aasync(join);

  /* Close MAAPI sockets used for init */
  
  for(node = aasync_nodes; node != NULL; node = node->next) {
    close(node->maapi_socket);
  }
  
  /* Handle CDB subscriber events */
  while (1) {
    struct pollfd set[3];

    set[0].fd = ctlsock;
    set[0].events = POLLIN;
    set[0].revents = 0;

    set[1].fd = workersock;
    set[1].events = POLLIN;
    set[1].revents = 0;
    
    set[2].fd = subsock_cfg;
    set[2].events = POLLIN;
    set[2].revents = 0;

    if (poll(set, sizeof(set)/sizeof(*set), -1) < 0) {
      perror("Poll failed:");
      continue;
    }
    /* Check for I/O */
    if (set[0].revents & POLLIN) {
      if ((ret = confd_fd_ready(dctx, ctlsock)) == CONFD_EOF) {
	confd_fatal("aasync%d: Control socket closed", local_nodeid);
      } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
	confd_fatal("Error on control socket request: %s (%d): %s",
		    confd_strerror(confd_errno), confd_errno, confd_lasterr());
      }
    }
    else if (set[1].revents & POLLIN) {
      if ((ret = confd_fd_ready(dctx, workersock)) == CONFD_EOF) {
	confd_fatal("aasync%d: Worker socket closed", local_nodeid);
      } else if (ret == CONFD_ERR && confd_errno != CONFD_ERR_EXTERNAL) {
	confd_fatal("aasync%d: Error on worker socket request: %s (%d): %s", local_nodeid,
		    confd_strerror(confd_errno), confd_errno, confd_lasterr());
      }
    }
    else if (set[2].revents & POLLIN) {
      /* Handle CDB modifications subscriber event */
      if ((ret = cdb_read_subscription_socket2(subsock_cfg,
					       &type,
					       NULL,
					       &subp,
					       &reslen)) != CONFD_OK) {
	if (ret == CONFD_EOF) {
	  exit(0);
	}
	confd_fatal("aasync%d: cdb_read_subscription_socket failed", local_nodeid);
      }
      if (reslen > 0) {
	switch (type) {
	case CDB_SUB_PREPARE:
	  DEBUG_LOG("aasync%d: TYPE=CDB_SUB_PREPARE", local_nodeid);

	  if(aasync_usr) { /* if the user name begin with "aasync" we have been replicated to by another aasync node */
	    nvals = 0;
	    if ((ret = cdb_sync_subscription_socket(subsock_cfg, CDB_DONE_PRIORITY)) != CONFD_OK) {
	      confd_fatal("aasync%d: failed to sync subscription", local_nodeid);
	    }
	    break;
	  }

	  /* Get the CDB modifications in tag value array format */
	  if ((ret = cdb_get_modifications(subsock_cfg, 
					   *subp,
					   CDB_GET_MODS_INCLUDE_LISTS, 
					   &tvals, 
					   &nvals,
					   ACTIVE_CFG_PATH)) != CONFD_OK) {
	    confd_fatal("aasync%d: failed to get modifications", local_nodeid);
	  } else if (nvals == 0) {
	    DEBUG_LOG("aasync%d: no modifications", local_nodeid);
	  } else { /* got modifications */
#ifdef DO_DEBUG_LOG
	    print_modifications(tvals, nvals, NULL, 0);
#endif
	    DEBUG_LOG("aasync%d: get modifications nvals %d", local_nodeid, nvals);
	    
	    for(node = aasync_nodes; node != NULL; node = node->next) {
	      if(node->nodeid != local_nodeid) {
		/* Open up MAAPI sessions other active CDBs */
		if((ret = maapi_socket(&(node->maapi_socket), &(node->addr))) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi socket connect to node %d failed", local_nodeid, node->nodeid);
		  goto abort_local_trans;
		}
		/* Start the maapi session */
		ip.af = node->addr.sin_family;
		ip.ip.v4 = (struct in_addr) node->addr.sin_addr;

		if ((ret = maapi_start_user_session(node->maapi_socket, progname, progname,
						    groups, sizeof(groups) / sizeof(*groups),
						    &ip, CONFD_PROTO_TCP)) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi_start_user session to node %d failed", local_nodeid, node->nodeid);
		  goto abort_local_trans;
		}
		/* Take a northbound API (e.g. NETCONF, REST, ..) write lock on other active CDBs */
		/* By taking a global write lock we avoid risking deadlock situations by making sure 
		   that there is no other transaction in progress on the other node */
		DEBUG_LOG("aasync%d: maapi_lock to node %d", local_nodeid, node->nodeid);
		i=0;
		while((ret = maapi_lock(node->maapi_socket, CONFD_RUNNING)) != CONFD_OK) {
		  if(i == NUM_LOCK_RETRIES) {
		    DEBUG_LOG("aasync%d: maapi_lock to node %d failed. Aborting transaction...", local_nodeid, node->nodeid);
		    goto abort_local_trans;
		  }
		  i++;
		  DEBUG_LOG("aasync%d: maapi_lock to node %d failed. Retry %d of %d", local_nodeid, node->nodeid, i, NUM_LOCK_RETRIES);
		  sleep(1);
		}
	      }	
	    }

	    for(node = aasync_nodes; node != NULL; node = node->next) {
	      if(node->nodeid != local_nodeid) {
		if (((node->th = maapi_start_trans(node->maapi_socket, CONFD_RUNNING, CONFD_READ_WRITE))) < 0) {
		  DEBUG_LOG("aasync%d: maapi_start_trans to node%d failed", local_nodeid, node->nodeid);
		  goto abort_local_trans;
		}
		  
		/* Write the CDB modifications we got in tag value format and write them to the other active ConfDs */
		if ((ret = maapi_set_values(node->maapi_socket, node->th, tvals, nvals, ACTIVE_CFG_PATH)) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi_set_values to node %d failed", local_nodeid, node->nodeid);
		  goto abort_local_trans;
		}
		  
		if (maapi_validate_trans(node->maapi_socket, node->th, 0, 0) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi_validate_trans to node %d failed", local_nodeid, node->nodeid);
		  goto abort_local_trans;
		}
	      }
	    }
	    /* We divide the write + validate and prepare into two steps to minimize the time our nodes synched to is unavailable. The maapi_lock() on 
	       the northbound interfaces will be released by the node itself when validation phase is entered and the transaction lock is taken */
	    for(node = aasync_nodes; node != NULL; node = node->next) {
	      if(node->nodeid != local_nodeid) {
		if (maapi_prepare_trans(node->maapi_socket, node->th) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi_prepare_trans to node %d failed", local_nodeid, node->nodeid);
		  goto abort_local_trans;
		}
	      }
	    }
	  }
	  free_tag_values(tvals, nvals);
	  free(tvals);
	  if ((ret = cdb_sync_subscription_socket(subsock_cfg, CDB_DONE_PRIORITY)) != CONFD_OK) {
	    confd_fatal("failed to sync subscription");
	  }
	  break;
	abort_local_trans:
	  free_tag_values(tvals, nvals);
	  free(tvals);
	  /* abort all aasync transactions by closing the session */
	  for(node = aasync_nodes; node != NULL; node = node->next) {
	      if(node->nodeid != local_nodeid) {
		close(node->maapi_socket);
	      }
	  }	  
	  /* abort local transaction */
	  if ((ret = cdb_sub_abort_trans(subsock_cfg, CONFD_ERRCODE_RESOURCE_DENIED,
					 0, 0, "Synchronization to other active ConfD nodes failed"))
	      != CONFD_OK) {
	    confd_fatal("failed to abort the transaction");
	  }
	  break;
	case CDB_SUB_COMMIT:
	  DEBUG_LOG("aasync%d: TYPE=CDB_SUB_COMMIT", local_nodeid);
	  if(nvals > 0 && !aasync_usr) { /* if no modifications were done or user is "aasync" there is nothing to commit */
	    /* Commit the MAAPI transaction towards all other active ConfDs */
	    for(node = aasync_nodes; node != NULL; node = node->next) {
	      if(node->nodeid != local_nodeid) {
		if (maapi_commit_trans(node->maapi_socket, node->th) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi_commit_trans to node %d failed", local_nodeid, node->nodeid);
	        }
	        if (maapi_finish_trans(node->maapi_socket, node->th) != CONFD_OK) {
		  DEBUG_LOG("aasync%d: maapi_finish_trans to node %d failed", local_nodeid, node->nodeid);
	        }
	      }
	    }

	    for(node = aasync_nodes; node != NULL; node = node->next) {
	      if(node->nodeid != local_nodeid) {
		/* No need to relese the write lock on CDB. Closing the session will release the write lock */
		/* Close the MAAPI sessions to other active ConfD nodes */
		close(node->maapi_socket);
	      }
	    }
	  }
	  /* Get the CDB modifications for aacluster in tag value array format */
	  if ((ret = cdb_get_modifications(subsock_cfg, 
					   *subp, 
					   CDB_GET_MODS_INCLUDE_LISTS, 
					   &tvals, 
					   &nvals,
					   AACLUSTER_PATH)) == CONFD_OK) {
	      /* Handle the CDB modifications we got in tag value format and write them to the 
		 local aasync_nodes list */ 
	      handle_aacluster_modifications(tvals, nvals);
	      free_tag_values(tvals, nvals);
	      free(tvals);     
	  }
	  if ((ret = cdb_sync_subscription_socket(subsock_cfg, CDB_DONE_PRIORITY)) != CONFD_OK) {
	    confd_fatal("failed to sync subscription");
	  }
	  break;
	case CDB_SUB_ABORT:
	  /* manager aborted the transaction release resources */
	  DEBUG_LOG("aasync%d: Transaction aborted by the manager, close aasync sockets and send CDB_DONE_PRIORITY", local_nodeid);
	  /* Close MAAPI sockets to other active ConfD nodes if they are open */
	  for(node = aasync_nodes; node != NULL; node = node->next) {
	    if(node->nodeid != local_nodeid) {
	      close(node->maapi_socket);
	    }
	  }
	  if ((ret = cdb_sync_subscription_socket(subsock_cfg, CDB_DONE_PRIORITY)) != CONFD_OK) {
	    confd_fatal("failed to sync subscription");
          }
	  break;
	default:
	  confd_fatal("unknown subtype");
          break;
	if (subp) { free(subp); }
	  /* Even through we are past the "point of no return" in the ConfD transaction, this transaction 
	     will not be over, i.e. another transaction will not be allowed to start, until after we now 
	     have handled the CDB modifications and synched them with the other active ConfDs */
	}
      }
    }
  }
}
