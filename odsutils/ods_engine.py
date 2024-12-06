import json
from astropy.time import Time
from copy import copy


def read_json_file(filename):
    if not filename.endswith('.json'):
        filename = filename + '.json'
    with open(filename, 'r') as fp:
        input_file = json.load(fp)
    return input_file


class ODS:
    """
    Utilities to read, update, write, and check ODS records.

    Maintains an internal self.ods record list that gets manipulated.

    """
    ods_fields = {
        'site_id': str,
        'site_lat_deg': float,
        'site_lon_deg': float,
        'site_el_m': float,
        'src_id': str,
        'src_is_pulsar_bool': bool,
        'corr_integ_time_sec': float,
        'src_ra_j2000_deg': float,
        'src_dec_j2000_deg': float,
        'src_radius': float,
        'src_start_utc': str,
        'src_end_utc': str,
        'slew_sec': float,
        'trk_rate_dec_deg_per_sec': float,
        'trk_rate_ra_deg_per_sec': float,
        'freq_lower_hz': float,
        'freq_upper_hz': float,
        'notes': str
    }

    def __init__(self, quiet=False):
        self.quiet = quiet
        self.defaults = {}
        self.ods = []
        self.valid_records = []
        self.number_of_records = 0

    def qprint(self, msg):
        if not self.quiet:
            print(msg)

    def read_ods(self, ods_file_name):
        """
        Read in an existing ods file, check it and pull out input sets

        Parameter
        ---------
        ods_file_name : str
            Name of ods json file

        Attributes
        ----------
        ods_file_name : str
            The supplied ods file name
        ods : list
            List of ods records that is manipulated
        see self.check_ods/self._gen_input_sets for others

        """
        self.ods_file_name = ods_file_name
        input_ods_data = read_json_file(self.ods_file_name)
        self.ods = input_ods_data['ods_data']  # This is the internal list of ods records
        self.check_ods()
        self.qprint(f"Read {self.number_of_records} records from {self.ods_file_name}")
        number_of_invalid_records = self.number_of_records - len(self.valid_records)
        if number_of_invalid_records:
            print(f"{number_of_invalid_records} / {self.number_of_records} were not valid.")
        self._gen_input_sets()

    def _gen_input_sets(self):
        """
        Pull apart the existing valid ods records to get unique value sets

        Attribute
        ---------
        input_ods_sets : dict
            Dictionary of ods sets
        """
        self.input_ods_sets = {}  # 
        for irec in self.valid_records:
            for key, val in self.ods[irec].items():
                self.input_ods_sets.setdefault(key, set())
                self.input_ods_sets[key].add(val)

    def check_ods_record(self, rec, ctr=None):
        """
        Checks a single ods record.

        Parameters
        ----------
        rec : dict
            An ods record
        ctr : int or None
            If supplied, a counter of which record for printing
        
        Return
        ----------
        bool
            Is the record a valid ods record

        """
        ending = '' if ctr is None else f'in record {ctr}'
        is_valid = True
        for key in rec:  # check that all supplied keys are valid and not None
            if key not in self.ods_fields:
                self.qprint(f"{key} not an ods_field {ending}")
                is_valid = False
            elif rec[key] is None:
                self.qprint(f"Value for {key} is None {ending}")
                is_valid = False
        for key in self.ods_fields:  # Check that all keys are provided for a rec and type is correct
            if key not in rec:
                self.qprint(f"Missing {key} {ending}")
                is_valid = False
            if rec[key] is not None:
                try:
                    _ = self.ods_fields[key](rec[key])
                except ValueError:
                    self.qprint(f"{rec[key]} is wrong type for {key} {ending}")
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
        self.number_of_records = len(self.ods)

    def get_defaults_dict(self, defaults=':from_ods'):
        """
        Parameter
        ---------
        defaults : dict, str
            ods record default values (keys are ods_fields)
            - dict provides the actual default key/value pairs
            - str 
              (a) if starts with ':', uses "special case" of the from_ods input sets (can add options...)
              (b) is a filename with the defaults as a json
                  if there is a ':', then it is that filename preceding and the key after the :
        
        Attribute
        ---------
        defaults : dict
            Dictionary containing whatever ods records defaults are provided.

        """
        if defaults is None:  # No change to existing self.defaults
            return
        if isinstance(defaults, dict):
            self.defaults = defaults
            using_from = 'input_dict'
        elif isinstance(defaults, str):
            using_from = defaults
            if defaults[0] == ':':
                if defaults[1:] == 'from_ods':
                    self.defaults = {}
                    for key, val in self.input_ods_sets.items():
                        if len(val) == 1:
                            self.defaults[key] = list(val)[0]
                else:
                    print(f"Not valid default case: {defaults}")
            else:
                fnkey = defaults.split(':')
                self.defaults = read_json_file(fnkey[0])
                if len(fnkey) == 2:
                    self.defaults = self.defaults[fnkey[1]]
        self.qprint(f"Default values from {using_from}")
        for key, val in self.defaults.items():
            self.qprint(f"\t{key:26s}  {val}")

    def cull_ods_by_time(self, cull_time='now'):
        """
        Remove entries with end times before cull_time.  Overwrites self.ods.

        Parameter
        ---------
        cull_time : str
            isoformat time string

        """
        if cull_time == 'now':
            cull_time = Time.now()
        else:
            cull_time = Time(cull_time)
        self.qprint(f"Culling ODS for {cull_time}")
        culled_ods = []
        for rec in self.ods:
            end_time = Time(rec['src_end_utc'])
            if end_time > cull_time:
                culled_ods.append(rec)
        self.ods = copy(culled_ods)

    def cull_ods_by_invalid(self):
        """
        Remove entries that fail validity check.

        """
        self.qprint("Culling ODS for invalid records")
        self.check_ods()
        if len(self.valid_records) == self.number_of_records:
            return
        culled_ods = []
        for irec in self.valid_records:
            culled_ods.append(copy(self.ods[irec]))
        self.ods = culled_ods

    def new_record(self, init_value=None):
        """
        Generate a full record, with each value set by init_value.

        Parameter
        ---------
        init_value : anything
            Whatever you want, however, if a dict, it will assume the dict has ods_field values to use and others set to None

        Return
        ------
        dict
            A new ods record

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

    def append_new_record_from_Namespace(self, ns, override=False):
        """
        Appends a new ods record to self.ods supplied as a Namespace
        Between defaults and kwargs, must be complete ods record.

        """
        kwargs = {}
        for key, val in vars(ns).items():
            if key in self.ods_fields:
                kwargs[key] = val
        self.append_new_record(override=override, **kwargs)

    def append_new_record(self, override=False, **kwargs):
        """
        Append a new record to self.ods, using defaults then kwargs.
        Between defaults and kwargs, must be complete ods record.

        """
        new_rec = self.new_record(self.defaults)
        new_rec.update(kwargs)
        is_valid = self.check_ods_record(new_rec)
        if is_valid or override:
            self.ods.append(new_rec)
        else:
            print("Not adding record.")

    def update_from_list(self, entries, override=False):
        """
        Parameters
        ----------
        entries : list of dicts
            List of dictionaries containing ODS fields
        override : bool
            add record regardless of passing ods checking

        """
        for entry in entries:
            self.append_new_record(override=override, **entry)
        self.check_ods()

    def update_from_file(self, data_file_name, defaults=None, override=False, sep="\s+", replace_char=None, header_map=None):
        """
        Append new records from a data file to self.ods; assumes the first line is a header.

        Parameters
        ----------
        data_file_name : str
            Name of input data file.
        defaults : dict, str
            ods record default values (keys are ods_fields)
            - dict provides the actual default key/value pairs
            - str 
              (a) if starts with ':', uses "special case" of the from_ods input sets (can add options...)
              (b) is a filename with the defaults as a json
                  if there is a ':', then it is that filename preceding and the key after the :
        override : bool
            add record regardless of passing ods checking
        sep : str
            separator
        replace_char : None, str, tuple, list
            replace characters in column headers
            - str: remove that character (replace with '')
            - tuple/list of length 1: same as above
            - tuple/list of length 2: replace [0] with [1]
        header_map : None, dict
            replace column header names with those provided {<datafile_header_name>: <ods_header_name>}

        """
        import pandas as pd

        self.get_defaults_dict(defaults)

        obs_list = pd.read_csv(data_file_name, sep=sep)
        if isinstance(replace_char, str):
            obs_list.columns = obs_list.columns.str.replace(replace_char, "")
        elif isinstance(replace_char, (list, tuple)):
            if len(replace_char) == 1:
                obs_list.columns = obs_list.columns.str.replace(replace_char[0], "")
            elif len(replace_char) == 2:
                obs_list.columns = obs_list.columns.str.replace(replace_char[0], replace_char[1])
        if isinstance(header_map, dict):  # rename the provided columns
            obs_list = obs_list.rename(header_map, axis='columns')

        for _, row in obs_list.iterrows():
            self.append_new_record(override=override, **row.to_dict())
        self.check_ods()

    def view_ods(self, order=['src_id', 'src_start_utc', 'src_end_utc'], number_per_block=5):
        """
        View the ods as a table arranged in blocks.

        Parameters
        ----------
        order : list
            First entries in table, rest of ods record values are append afterwards.
        number_per_block : int
            Number of records to view per block

        """
        if not self.number_of_records:
            return
        from tabulate import tabulate
        from numpy import ceil
        blocks = [range(i * number_per_block, (i+1) * number_per_block) for i in range(int(ceil(self.number_of_records / number_per_block)))]
        blocks[-1] = range(blocks[-1].start, self.number_of_records)
        order = order + [x for x in self.ods_fields if x not in order]
        for blk in blocks:
            data = []
            for key in order:
                row = [key] + [self.ods[i][key] for i in blk]
                data.append(row)
            print(tabulate(data))

    def std(self):
        """
        Print out the keys/types

        """
        from tabulate import tabulate
        data = []
        for key, val in self.ods_fields.items():
            data.append([key, val])
        print(tabulate(data, headers=['key', 'type']))

    def write_ods(self, file_name):
        """
        Export the ods to a json file.

        Parameter
        ---------
        file_name : str
            Name of ods json file to write

        """
        if not len(self.ods):
            print("WARNING: The ODS file is empty")
        ods2write = {'ods_data': self.ods}
        with open(file_name, 'w') as fp:
            json.dump(ods2write, fp, indent=2)