import argparse
from odsutils import ods_engine

ap = argparse.ArgumentParser()
ap.add_argument('-o', '--ods_file', help="Name of ods json file to read.", default=None)
ap.add_argument('-d', '--defaults', help="Name of json file holding default values", default=None)
ap.add_argument('--data_file', help="Name of data file to read", default=None)
ap.add_argument('--sep', help="Separator for the data file", default='\s+')
ap.add_argument('-c', '--cull', help="Cull existing ods file on time - 'now' or isoformat", default=False)
ap.add_argument('-i', '--invalid', help="Cull ods of invalid entries", action='store_true')
ap.add_argument('-w', '--write', help="Write ods to this file name", default=False)
ap.add_argument('-v', '--view', help="View ods", action='store_true')
# ODS fields
ap.add_argument('--site_id', help="ODS field", default=None)
ap.add_argument('--site_lat_deg', help="ODS field", default=None)
ap.add_argument('--site_lon_deg', help="ODS field", default=None)
ap.add_argument('--site_el_m', help="ODS field", default=None)
ap.add_argument('--src_id', help="ODS field", default=None)
ap.add_argument('--src_is_pulsar_bool', help="ODS field", default=None)
ap.add_argument('--corr_integ_time_sec', help="ODS field", default=None)
ap.add_argument('--src_ra_j2000_deg', help="ODS field", default=None)
ap.add_argument('--src_dec_j2000_deg', help="ODS field", default=None)
ap.add_argument('--src_radius', help="ODS field", default=None)
ap.add_argument('--src_start_utc', help="ODS field", default=None)
ap.add_argument('--src_end_utc', help="ODS field", default=None)
ap.add_argument('--slew_sec', help="ODS field", default=None)
ap.add_argument('--trk_rate_dec_deg_per_sec', help="ODS field", default=None)
ap.add_argument('--trk_rate_ra_deg_per_sec', help="ODS field", default=None)
ap.add_argument('--freq_lower_hz', help="ODS field", default=None)
ap.add_argument('--freq_upper_hz', help="ODS field", default=None)
ap.add_argument('--notes', help="ODS field", default=None)

args = ap.parse_args()

ods = ods_engine.ODS()
if args.ods_file:
    ods.read_ods(ods_file_name=args.ods_file)
    if args.defaults is None:
        args.defaults = ':single_valued'  # If nothing else defined, at least use this
if args.data_file:
    ods.update_from_file(data_file_name=args.data_file, defaults=args.defaults, sep=args.sep)
if args.src_id is not None:  # Assume that this one will always be used outside of defaults
    ods.append_new_record_from_Namespace(args)
if args.cull:
    ods.cull_ods_by_time(cull_time=args.cull)
if args.invalid:
    ods.cull_ods_by_invalid()
if args.view:
    ods.view_ods()
if args.write:
    ods.write_ods(file_name=args.write)