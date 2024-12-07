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

    meta_fields = {'data': 'ods_data'}


class Standard:
    """
    Wrapping class around individual standards.

    """
    def __init__(self, version):
        if version == 'latest':
            self.version = LATEST
        else:
            self.version = version
        self.read_version()

    def read_version(self):
        if self.version == 'A':
            self.standard = Standard_Version_A()
        self.ods_fields = self.standard.fields
        self.data_key = self.standard.meta_fields['data']

    def show(self):
        """Print out the keys/types of ods record"""

        from tabulate import tabulate
        data = []
        for key, val in self.ods_fields.items():
            data.append([key, val])
        print(tabulate(data, headers=['key', 'type']))