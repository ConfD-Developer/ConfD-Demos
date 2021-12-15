# Changing the log4j 2 Version


NSO use Apache Log4j 2 for Java log messages. This simple shell script help
change the version of the Log4j 2 jar files that are included with the NSO
release.

## Steps

1. Either source the ncsrc environment command file or run the script with the
   -h flag to get information on how to set the path to the jar file directory.
2. Run the script.

## Examples

Get help
```
$ ./nso_log4j2_upgrade.sh -h

Script for upgrading the log4j 2 version used by the NSO Java API

  -v  New Log4j 2 version. Default: 2.16.0
  -u  URL to the Apache Log4j 2 binary (tar.gz). Default: https://dlcdn.apache.org/logging/log4j/NEW_VERSION/apache-log4j-NEW_VERSION-bin.tar.gz
  -p  Path to the NSO Java API jar files. Default: NCS_DIR/java/jar
  -n  Path to the netsim ConfD Java API jar files. Default: NCS_DIR/netsim/confd/java/jar
  -k  URL to the KEYS for verifying the integrity of the Apache Log4j 2 distribution. Default: https://downloads.apache.org/logging/KEYS
  -s  URL to the asc signature file for verifying the integrity of the Apache Log4j 2 distribution. Default: https://downloads.apache.org/logging/log4j/NEW_VERSION/apache-log4j-NEW_VERSION-bin.tar.gz.asc
```
To, for example, upgrade to 2.16.0:
```
  $ source ncsrc; ./nso_log4j_2_upgrade.sh -v 2.16.0
```
