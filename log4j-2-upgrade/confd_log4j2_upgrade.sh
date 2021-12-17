#!/bin/bash
set -eu # Abort the script if a command returns with a non-zero exit code or if
        # a variable name is dereferenced when the variable hasn't been set

RED='\033[0;31m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

function usage()
{
   printf "${GREEN}Script for upgrading the log4j 2 version used by the ConfD Java API\n\n"
   printf "  -v  New Log4j 2 version. Default: 2.16.0\n"
   printf "  -u  URL to the Apache Log4j 2 binary (tar.gz). Default: https://www.apache.org/dyn/closer.lua/logging/log4j/NEW_VERSION/apache-log4j-NEW_VERSION-bin.tar.gz\n"
   printf "  -p  Path to the ConfD Java API jar files. Default: CONFD_DIR/java/jar\n"
   printf "  -k  URL to the KEYS for verifying the integrity of the Apache Log4j 2 distribution. Default: https://downloads.apache.org/logging/KEYS\n"
   printf "  -s  URL to the asc signature file for verifying the integrity of the Apache Log4j 2 distribution. Default: https://downloads.apache.org/logging/log4j/NEW_VERSION/apache-log4j-NEW_VERSION-bin.tar.gz.asc\n"
   printf "\nTo, for example, upgrade to 2.16.0:\n\n"
   printf "  \$ source confdrc; ./confd_log4j_2_upgrade.sh -v 2.16.0\n\n${NC}"
}

NEW_VERSION=2.16.0
LOG4J_2_URL="https://dlcdn.apache.org/logging/log4j/$NEW_VERSION/apache-log4j-$NEW_VERSION-bin.tar.gz"
KEYS_URL="https://downloads.apache.org/logging/KEYS"
SIGN_URL="https://downloads.apache.org/logging/log4j/$NEW_VERSION/apache-log4j-$NEW_VERSION-bin.tar.gz.asc"

# Retrieve the calling parameters.
while getopts "v:u:p:k:s:h" OPTION; do
    case "${OPTION}"
    in
        v)  NEW_VERSION="${OPTARG}";;
        u)  LOG4J_2_URL="${OPTARG}";;
        p)  JAR_PATH="${OPTARG}";;
        k)  KEYS_URL="${OPTARG}";;
        s)  SIGN_URL="${OPTARG}";;
        h)  usage; exit 0;;
        \?) printf "${RED}Invalid parameter${NC}"; usage; return 1;;
    esac
done

set +u
if [ -z "$JAR_PATH" ]; then
    if ! [ -z "${CONFD_DIR}" ]; then
        JAR_PATH=${CONFD_DIR}/java/jar
    else
        printf "${RED}Path to the ConfD Java API jar files or CONFD_DIR is not set. Aborting.${NC}\n\n"; usage; exit 1;
    fi
fi
set -u

hash curl 2>/dev/null || { printf "${RED}curl not installed. Aborting.${NC}\n"; exit 1; }
hash gpg 2>/dev/null || { printf "${RED}gpg not installed. Aborting.${NC}\n"; exit 1; }

printf "\n${PURPLE}Change directory to $JAR_PATH\n${NC}"
cd $JAR_PATH
printf "\n${PURPLE}Remove the old log4j 2 jar files\n${NC}"
/bin/rm -fv log4j-*.jar
printf "\n${PURPLE}Download keys, signature, and the log4j 2 $NEW_VERSION release from $LOG4J_2_URL\n${NC}"
curl -s $KEYS_URL --output KEYS
curl -s $SIGN_URL --output apache-log4j-$NEW_VERSION-bin.tar.gz.asc
curl -s $LOG4J_2_URL --output apache-log4j-$NEW_VERSION-bin.tar.gz
printf "\n${PURPLE}Use gpg to verify the integrity of the Apache Log4j 2 distribution\n${NC}"
gpg -v --import KEYS
gpg -v --verify apache-log4j-$NEW_VERSION-bin.tar.gz.asc apache-log4j-$NEW_VERSION-bin.tar.gz
printf "\n${PURPLE}Extract the Apache Log4j 2 distribution tarball\n${NC}"
tar xvfz apache-log4j-$NEW_VERSION-bin.tar.gz
printf "\n${PURPLE}Replace the existing log4j 2 core and api jar files with the new $NEW_VERSION version\n${NC}"
mv -vf ./apache-log4j-$NEW_VERSION-bin/log4j-core-$NEW_VERSION.jar .
mv -vf ./apache-log4j-$NEW_VERSION-bin/log4j-api-$NEW_VERSION.jar .
cp -vf log4j-core-$NEW_VERSION.jar log4j-core.jar
cp -vf log4j-api-$NEW_VERSION.jar log4j-api.jar
printf "\n${PURPLE}Cleanup\n${NC}"
rm -rvf ./apache-log4j-$NEW_VERSION-bin*
rm -vf KEYS
printf "\n${GREEN}Done\n${NC}"
