LATEST = 'A'

class Standard_Version_A:
    """
    Contains elements defining the ODS standard for Version A (rename as it comes along)

    Expand as versions come along -- currently very clunky!

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

    meta_fields = {'data_key': 'ods_data',
                   'time_fields': ['src_start_utc', 'src_end_utc']}

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
        # Probably not the best place to carry this, but...
        self.plot_azel = 'Az vs El'
        self.plot_timeel = 'Time vs El'

    def __str__(self):
        """Print out the keys/types of ods record"""

        from tabulate import tabulate
        data = []
        for key, val in self.ods_fields.items():
            data.append([key, val])
        return tabulate(data, headers=['key', 'type'])

    def read_version(self):
        """
        Read the appropriate version info into this class.

        """
        if self.version == 'A':
            self.standard = Standard_Version_A()
        self.ods_fields = self.standard.fields
        self.data_key = self.standard.meta_fields['data_key']
        self.time_fields = self.standard.meta_fields['time_fields']
        for key, val in self.standard.transfer_keys.items():
            setattr(self, key, val)