from . import ods_tools as tools
from astropy.time import TimeDelta


class ODSCheck(tools.Base):
    """
    Utilities to check ODS instances/records.

    """
    prefixes = {'n': '', 'w': 'WARNING: ', 'e': 'ERROR: '}

    def __init__(self, alert='warn', standard=None):
        """
        Parameter
        ---------
        alert : str
            Default alert

        """
        self.quiet = True if alert == 'none' else False
        self.pre = self.prefixes[alert[0].lower()]
        self.standard = standard

    def update_standard(self, standard):
        self.standard = standard

    def record(self, rec, ctr=None, standard=None):
        """
        Checks a single ods record for:
            1 - keys are all valid ODS fields
            2 - values are all consistent with ODS field type
            3 - all fields are present
            4 - time fields are parseable by astropy.time.Time

        Parameters
        ----------
        rec : dict
            An ods record
        ctr : int or None
            If supplied, a counter of which record for printing
        stanrdard : Standard or None
            Standard to use
        
        Return
        ----------
        bool
            Is the record a valid ods record

        """
        standard = self.standard if standard is None else standard

        ending = '' if ctr is None else f'in record {ctr}'
        is_valid = True
        for key in rec:  # check that all supplied keys are valid and not None
            if key not in standard.ods_fields:
                self.qprint(f"{self.pre}{key} not an ods_field {ending}")
                is_valid = False
            elif rec[key] is None:
                self.qprint(f"{self.pre}Value for {key} is None {ending}")
                is_valid = False
        for key in standard.ods_fields:  # Check that all keys are provided for a rec and type is correct
            if key not in rec:
                self.qprint(f"{self.pre}Missing {key} {ending}")
                is_valid = False
            if rec[key] is not None:
                try:
                    _ = standard.ods_fields[key](rec[key])
                except ValueError:
                    self.qprint(f"{self.pre}{rec[key]} is wrong type for {key} {ending}")
                    is_valid = False
        for key in standard.time_fields:
            try:
                _ = tools.make_time(rec[key])
            except ValueError:
                self.qprint(f"{self.pre}{rec[key]} is not a valid astropy.time.Time input format {ending}")
                is_valid = False
        return is_valid

    def ods(self, ods):
        """
        Checks the ods instance records are correct and complete.

        Parameter
        ---------
        ods : ODS instance
            ODS instance to check

        Returns
        -------
        valid_records : list
            List of valid record entries in the ODS instance

        """
        valid_records = []
        for ctr, rec in enumerate(ods.entries):
            is_valid = self.record(rec, ctr, standard=ods.standard)
            if is_valid:
                valid_records.append(ctr)
        return valid_records
    
    def is_same(self, rec1, rec2, standard=None):
        """
        Checks to see if two records are equal.

        Parameters
        ----------
        rec1 : dict
            ODS record
        rec2 : dict
            ODS record
        standard : Standard Class
            Standard to use

        Return
        ------
        bool : True if the entries are the same

        """
        standard = self.standard if standard is None else standard
        for key in standard.ods_fields:
            try:
                if str(rec1[key]) != str(rec2[key]):
                    return False
            except KeyError:  # Doesn't check across standards.
                return False
        return True

    def is_duplicate(self, ods, record):
        """
        Checks the ods for the record.

        Parameters
        ----------
        ods : ODS Instance
            ODS Instance to check
        record : dict
            Reord to check

        Return
        ------
        bool : True if the record is already in ODS Instance

        """
        for entry in ods.entries:
            if self.is_same(entry, record, standard=ods.standard):
                return True
        return False

    def observation(self, rec, el_lim_deg=10.0, dt_sec=120.0, show_plot=False, standard=None):
        """
        Determine whether an ODS record represents a source above the horizon.

        Parameters
        ----------
        rec : dict
            ODS record
        el_lim_deg : float
            Elevation limit that represents "above the horizon"
        dt_sec : float
            Time step for ephemerides check.
        show_plot : bool
            Show the plot of ephemerides.
        stanrdard : Standard or None
            Standard to use

        Return
        ------
        tuple or False
            False if never above the horizon, otherwise a tuple containing the limiting times within the record span.

        """
        from astropy.coordinates import EarthLocation, AltAz, SkyCoord
        import astropy.units as u
        from numpy import where

        standard = self.standard if standard is None else standard
        start = tools.make_time(rec[standard.start])
        stop = tools.make_time(rec[standard.stop])
        dt = TimeDelta(dt_sec, format='sec')
        times = []
        this_step = start
        while(this_step < stop):
            times.append(this_step)
            this_step += dt
        times = tools.make_time(times)
        location = EarthLocation(lat = float(rec[standard.lat]) * u.deg, lon = float(rec[standard.lon]) * u.deg, height = float(rec[standard.ele]) * u.m)

        aa = AltAz(location=location, obstime=times)
        coord = SkyCoord(float(rec[standard.ra]) * u.deg, float(rec[standard.dec]) * u.deg)
        obs = coord.transform_to(aa)
        above_horizon = where(obs.alt > el_lim_deg * u.deg)[0]
        if not len(above_horizon):
            return False
        if show_plot:
            import matplotlib.pyplot as plt
            plt.figure(standard.plot_azel)
            plt.plot(obs.az, obs.alt, label=rec[standard.source])
            plt.figure(standard.plot_timeel)
            plt.plot(times.datetime, obs.alt, label=rec[standard.source])
        return (times[above_horizon[0]].datetime.isoformat(timespec='seconds'), times[above_horizon[-1]].datetime.isoformat(timespec='seconds'))
    
    def continuity(self, ods, time_offset_sec=1, adjust='stop'):
        """
        Check whether records overlap.

        This assumes that the list is fairly reasonable and doesn't do anything very smart at this point.

        Parameters
        ----------
        ods : list
            ODS list of records
        time_offset_sec : float
            Time used to offset overlapping entries
        adjust : str
            Adjust 'start' or 'stop'

        Return
        ------
        Adjusted ODS list of records

        """
        if adjust not in ['start', 'stop']:
            self.qprint(f'WARNING: Invalid adjust spec - {adjust}')
            return ods
        adjusted_entries = tools.sort_entries(ods, [ods.standard.start, ods.standard.stop])
        for i in range(len(adjusted_entries) - 1):
            this_stop = tools.make_time(adjusted_entries[i][ods.standard.stop])
            next_start = tools.make_time(adjusted_entries[i+1][ods.standard.start])
            if next_start < this_stop:  # Need to adjust
                if adjust == 'start':
                    next_start = this_stop + TimeDelta(time_offset_sec, format='sec')
                elif adjust == 'stop':
                    this_stop = next_start - TimeDelta(time_offset_sec, format='sec')
                adjusted_entries[i].update({ods.standard.stop: this_stop.datetime.isoformat()})
                adjusted_entries[i+1].update({ods.standard.start: next_start.datetime.isoformat()})
                if next_start < this_stop:
                    self.qprint(f"{self.pre}New start is before stop so still need to fix.")
        return adjusted_entries

    def coverage(self, ods, time_step_min=1):
        """
        Check coverage of records in an ODS instance.

        Parameters
        ----------
        ods : list
            ODS list of records
        time_step_min : float
            Time step to check in minutes

        Return
        ------
        float : fraction of time covered

        """

        sorted_entries = tools.sort_entries(ods.entries, [ods.standard.start, ods.standard.stop])
        ods_start, ods_stop = tools.make_time(sorted_entries[0][ods.standard.start]), tools.make_time(sorted_entries[-1][ods.standard.stop])
        print(f"Checking coverage from {ods_start} - {ods_stop}")
        dt = TimeDelta(time_step_min * 60.0, format='sec')
        this_time = ods_start - dt
        while this_time < ods_stop:
            this_time += dt
            for entry in sorted_entries:
                print("CHECK")