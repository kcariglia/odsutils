#! /usr/bin/env python

import argparse
from odsutils import ods_engine

ap = argparse.ArgumentParser()
ap.add_argument('--url', help="URL to monitor", default="https://www.seti.org/sites/default/files/HCRO/ods.json")
ap.add_argument('--logfile', help="Name of monitor log file", default='online_ods_mon.txt')
ap.add_argument('--add_header', help="Flag to include a header line in the file", action='store_true')
args = ap.parse_args()

ods = ods_engine.ODS()
ods.online_ods_log(url=args.url, logfile=args.logfile, add_header=args.add_header)