#! /usr/bin/env python

import argparse
from odsutils import ods_engine

ap = argparse.ArgumentParser()
ap.add_argument('--url', help="URL to monitor", default="https://www.seti.org/sites/default/files/HCRO/ods.json")
ap.add_argument('--logfile', help="Name of monitor log file", default='online_ods_mon.txt')
ap.add_argument('--version', help="Version type to check for", default='latest')
args = ap.parse_args()

ods = ods_engine.ODS(version=args.version)
ods.online_ods_monitor(url=args.url, logfile=args.logfile)