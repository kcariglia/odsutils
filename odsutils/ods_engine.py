import json
from astropy.time import Time
from copy import copy



class ODS:
    """
    Utilities to read, update, write, and check ODS records.

    Maintains an internal self.ods record list that gets manipulated.

    """
    ods_fields = [
        'site_id',
        'site_lat_deg',
        'site_lon_deg',
        'site_el_m',
        'src_id',
        'src_is_pulsar_bool',
        'corr_integ_time_sec',
        'src_ra_j2000_deg',
        'src_dec_j2000_deg',
        'src_radius',
        'src_start_utc',
        'src_end_utc',
        'slew_sec',
        'trk_rate_dec_deg_per_sec',
        'trk_rate_ra_deg_per_sec',
        'freq_lower_hz',
        'freq_upper_hz',
        'notes'
    ]

    def __init__(self):
        self.defaults = {}
        self.ods = []
        self.valid_records = []

    def read_ods(self, ods_file_name):
        """
        Read in an existing ods file, check it and pull out input sets

        Parameter
        ---------
        ods_file_name : str
            Name of ods json file

        """
        self.ods_file_name = ods_file_name
        with open(self.ods_file_name, 'r') as fp:
            input_ods_data = json.load(fp)
        self.ods = input_ods_data['ods_data']  # This is the internal list of ods records
        self.check_ods()
        print(f"Read {self.number_of_records} records from {self.ods_file_name}")
        number_of_invalid_records = self.number_of_records - len(self.valid_records)
        if number_of_invalid_records:
            print(f"{number_of_invalid_records} / {self.number_of_records} were not valid.")
        self._gen_input_sets()

    def _gen_input_sets(self):
        self.input_ods_sets = {}  # Pull apart the existing ods to get unique value sets
        for irec in self.valid_records:
            for key, val in self.ods[irec].items():
                self.input_ods_sets.setdefault(key, set())
                self.input_ods_sets[key].add(val)

    def check_ods_record(self, rec, ctr=None):
        """
        Checks a single ods record.
        """
        is_valid = True
        for key in rec:
            if key not in self.ods_fields:
                if ctr is None:
                    print(f"{key} not an ods_field")
                else:
                    print(f"{key} not an ods_field in record {ctr}")
                is_valid = False
            elif rec[key] is None:
                if ctr is None:
                    print(f"Value for {key} is None")
                else:
                    print(f"Value for {key} is None for record {ctr}")
                is_valid = False
        for key in self.ods_fields:
            if key not in rec:
                if ctr is None:
                    print(f"Missing {key}")
                else:
                    print(f"Record {ctr} missing {key}")
                is_valid = False
        return is_valid

    def check_ods(self):
        """
        Checks the ods records that they are correct and complete.

        Attributes
        ----------
        self.valid_records : list
            List of valid record entries in the list
        self.number_of_records : int
            Number of records checked.

        """
        self.valid_records = []
        for ctr, rec in enumerate(self.ods):
            is_valid = self.check_ods_record(rec, ctr)
            if is_valid:
                self.valid_records.append(ctr)
        self.number_of_records = ctr + 1

    def get_defaults_dict(self, defaults=':single_valued'):
        """
        Parameter
        ---------
        defaults : dict, str
            ods record default values (keys are ods_fields)
            - dict provides the actual default key/value pairs
            - str 
              (a) if starts with ':', uses "special case" of the single_valued input sets (can add options...)
              (b) is a filename with the defaults as a json
                  if there is a ':', then it is that filename preceding and the key after the :

        """
        if defaults is None:
            return
        if isinstance(defaults, dict):
            self.defaults = defaults
            using_from = 'input_dict'
        elif isinstance(defaults, str):
            using_from = defaults
            if defaults[0] == ':':
                if defaults[1:] == 'single_valued':
                    self._single_valued_defaults()
                else:
                    print(f"Not valid default case: {defaults}")
            else:
                fnkey = defaults.split(':')
                with open(fnkey[0], 'r') as fp:
                    self.defaults = json.load(fp)
                if len(fnkey) == 2:
                    self.defaults = self.defaults[fnkey[1]]
        print(f"Default values from {using_from}")
        for key, val in self.defaults.items():
            print(f"\t{key:26s}  {val}")

    def _single_valued_defaults(self):
        self.defaults = {}
        for key, val in self.input_ods_sets.items():
            if len(val) == 1:
                self.defaults[key] = list(val)[0]

    def cull_ods_by_time(self, cull_time='now'):
        """
        Remove entries with end times before cull_time.

        """
        if cull_time == 'now':
            cull_time = Time.now()
        else:
            cull_time = Time(cull_time)
        print(f"Culling ODS for {cull_time}")
        culled_ods = []
        for rec in self.ods:
            end_time = Time(rec['src_end_utc'])
            if end_time > cull_time:
                culled_ods.append(rec)
        self.ods = copy(culled_ods)

    def new_record(self, init_value=None):
        """
        Generate a full record, with each value set by init_value.

        Parameter
        ---------
        init_value : anything
            Whatever you want, however, if a dict, it will assume the dict has ods_field values to use and others set to None

        """
        rec = {}
        for key in self.ods_fields:
            if isinstance(init_value, dict):
                if key in init_value:
                    rec[key] = init_value[key]
                else:
                    rec[key] = None
            else:
                rec[key] = init_value
        return rec

    def append_new_record_from_Namespace(self, ns):
        kwargs = {}
        for key, val in vars(ns):
            if key in self.ods_fields:
                kwargs[key] = val
        self.append_new_record(**kwargs)

    def append_new_record(self, **kwargs):
        """
        Append a new record to the ods, using defaults then kwargs

        """
        new_rec = self.new_record(self.defaults)
        new_rec.update(kwargs)
        is_valid = self.check_ods_record(new_rec)
        if is_valid:
            self.ods.append(new_rec)
        else:
            print("Not adding record.")

    def update_from_file(self, data_file_name, defaults=None, sep="\s+"):
        """
        Append new records from a data file.

        """
        import pandas as pd

        self.get_defaults_dict(defaults)

        obs_list = pd.read_csv(data_file_name, sep=sep)
        obs_list.columns = obs_list.columns.str.replace("#", "")

        for _, row in obs_list.iterrows():
            self.append_new_record(**row.to_dict())

    def view_ods(self):
        from tabulate import tabulate
        print("View it...")

    def write_ods(self, file_name):
        ods2write = {'ods_data': self.ods}
        with open(file_name, 'w') as fp:
            json.dump(ods2write, fp, indent=2)