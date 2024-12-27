from . import ods_tools as tools

DEFAULT_WORKING_INSTANCE = 'primary'
LATEST = 'A'
PLOT_AZEL = 'Az vs El'
PLOT_TIMEEL = 'Time vs El'
REF_LATEST_TIME = '2026-12-31T23:59'
REF_EARLIEST_TIME = '2020-01-01T00:00'

class Standard_Version_A:
    """
    Contains elements defining the ODS standard for Version A (rename as it comes along)

    Expand as versions come along -- currently very clunky!  The version numbers should probably be JSON files

    """
    fields = {
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

    sort_order_time = ['src_start_utc', 'src_end_utc', 'site_id', 'site_lat_deg', 'site_lon_deg', 'site_el_m',
                       'src_id', 'src_is_pulsar_bool', 'corr_integ_time_sec', 'src_ra_j2000_deg', 'src_dec_j2000_deg', 'src_radius',
                       'slew_sec', 'trk_rate_dec_deg_per_sec', 'trk_rate_ra_deg_per_sec', 'freq_lower_hz', 'freq_upper_hz', 'notes']


    def __init__(self):
        self.transfer_keys = {
            'observatory': 'site_id',
            'lat': 'site_lat_deg',
            'lon': 'site_lon_deg',
            'ele': 'site_el_m',
            'source': 'src_id',
            'ra': 'src_ra_j2000_deg',
            'dec': 'src_dec_j2000_deg',
            'start': 'src_start_utc',
            'stop': 'src_end_utc'
        }
        self.meta_fields = {'data_key': 'ods_data',
                            'time_fields': ['src_start_utc', 'src_end_utc']}

class Standard:
    """
    Wrapping class around individual standards.

    This is awaiting input from NRAO, who said they are looking at different versions.

    """
    def __init__(self, version):
        """
        Parameter
        ---------
        version : str
            Version designator, 'latest' will get last.  Placeholder for now.

        """
        if version == 'latest':
            self.version = LATEST
        else:
            self.version = version
        self.read_version()

    def __str__(self):
        """Print out the keys/types of ods record"""

        from tabulate import tabulate
        data = []
        for key, val in self.ods_fields.items():
            data.append([key, val])
        hdr = f"| STANDARD VERSION {self.version} |"
        ddd = '-' * len(hdr)
        return f"{ddd}\n{hdr}\n{ddd}\n" + tabulate(data, headers=['key', 'type'])

    def read_version(self):
        """
        Read the appropriate version info into this class.

        """
        if self.version == 'A':
            self.standard = Standard_Version_A()
        self.ods_fields = self.standard.fields
        self.sort_order_time = self.standard.sort_order_time
        self.data_key = self.standard.meta_fields['data_key']
        self.time_fields = self.standard.meta_fields['time_fields']
        for key, val in self.standard.transfer_keys.items():
            setattr(self, key, val)

    def valid(self, rec):
        """
        Checks a single ods record for:
            1 - keys are all valid ODS fields
            2 - values are all consistent with ODS field type
            3 - all fields are present
            4 - time fields are parseable by astropy.time.Time

        Parameter
        ---------
        rec : dict
            An ods record
        
        Return
        ----------
        bool
            Is the record a valid ods record
        list of str
            Messages about validity check

        """
        is_valid = True
        msg = []
        for key in rec:  # check that all supplied keys are valid and not None
            if key not in self.ods_fields:
                msg.append(f"{key} not an ods_field")
                is_valid = False
            elif rec[key] is None:
                msg.append(f"Value for {key} is None")
                is_valid = False
        for key in self.ods_fields:  # Check that all keys are provided for a rec and type is correct
            if key not in rec:
                msg.append(f"Missing ODS field {key}")
                is_valid = False
            elif rec[key] is not None:
                try:
                    _ = self.ods_fields[key](rec[key])
                except ValueError:
                    msg.append(f"{rec[key]} is wrong type for {key}")
                    is_valid = False
        for key in self.time_fields:
            try:
                _ = tools.make_time(rec[key])
            except ValueError:
                msg.append(f"{rec[key]} is not a valid astropy.time.Time input format")
                is_valid = False
        return is_valid, msg