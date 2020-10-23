#!/usr/bin/env python3
import argparse
import os
import subprocess
from bs4 import BeautifulSoup
import re


def tailf_sanitize(yang_file):
    confd_dir = os.environ['CONFD_DIR']
    yang_path = yang_file.rsplit('/', 1)[0]
    result = subprocess.run(['python3', '/usr/local/bin/pyang', '-f', 'yin',
                            '-p', yang_path, '-p', confd_dir, yang_file],
                            stdout=subprocess.PIPE, encoding='utf-8')
    yin_content = result.stdout
    yin_content = yin_content.replace('tailf:', 'tailf_prefix_')
    yin_soup = BeautifulSoup(yin_content, "xml")
    for tailf_extension in yin_soup.find_all(re.compile('tailf_prefix_')):
        tailf_extension.decompose()
    tailf_import = yin_soup.find('import', module='tailf-common')
    if tailf_import is not None:
        tailf_import.decompose()
    yang_content = subprocess.run(['python3', '/usr/local/bin/pyang', '-f',
                                   'yang', '-p', yang_path, '-p', confd_dir],
                                   stdout=subprocess.PIPE, input=str(yin_soup),
                                   encoding='utf-8')
    print(yang_content.stdout, end='\r')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('filename', nargs=1, type=str,
                        help='<file> YANG module to be sanitized')
    args = parser.parse_args()
    tailf_sanitize(args.filename[0])
