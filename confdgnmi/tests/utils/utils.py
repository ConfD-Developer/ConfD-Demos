# add common tailf stuff here

import logging

logging.basicConfig(
    format='%(asctime)s:%(relativeCreated)s %(levelname)s:%(filename)s:%(lineno)s:%(funcName)s  %(message)s',
    level=logging.DEBUG)
log = logging.getLogger('pytest')
log.setLevel(logging.INFO)


def nodeid_to_path(nodeid):
    log.debug("==> nodeid_to_path nodeid=%s" % nodeid)
    nodeid = nodeid.replace("(", "")
    nodeid = nodeid.replace(")", "")
    nodeid = nodeid.replace("::", "_")
    nodeid = nodeid.replace("/", "_")
    log.debug("<== nodeid_to_path nodeid=%s" % nodeid)
    return nodeid
