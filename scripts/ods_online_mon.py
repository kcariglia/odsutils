#! /usr/bin/env python

import argparse
from odsutils import ods_engine

ap = argparse.ArgumentParser()
ap.add_argument('--url', help="URL to monitor", default="https://www.seti.org/sites/default/files/HCRO/ods.json")
ap.add_argument('--logfile', help="Name of monitor log file", default='online_ods_mon.txt')
ap.add_argument('--version', help="Version type to check for", default='latest')
ap.add_argument('--cols', help="Columns to output to monitor file -- 'all' or csv-list.", default='all')
ap.add_argument('--output', help="Logging output level", default='INFO')
args = ap.parse_args()

ods = ods_engine.ODS(version=args.version, output=args.output.upper())
ods.online_ods_monitor(url=args.url, logfile=args.logfile, cols=args.cols)