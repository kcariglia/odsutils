from .ods_tools import Base
from astropy.time import Time, TimeDelta


class ODSCheck(Base):
    """
    Utilities to check ODS records.

    """
    prefixes = {'n': '', 'w': 'WARNING: ', 'e': 'ERROR: '}

    def __init__(self, standard, alert='warn'):
        self.standard = standard
        self.alert = alert
        self.quiet = True if alert == 'none' else False
        self.pre = self.prefixes[alert[0].lower()]

    def record(self, rec, ctr=None):
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
        
        Return
        ----------
        bool
            Is the record a valid ods record

        """
        ending = '' if ctr is None else f'in record {ctr}'
        is_valid = True
        for key in rec:  # check that all supplied keys are valid and not None
            if key not in self.standard.ods_fields:
                self.qprint(f"{self.pre}{key} not an ods_field {ending}")
                is_valid = False
            elif rec[key] is None:
                self.qprint(f"{self.pre}Value for {key} is None {ending}")
                is_valid = False
        for key in self.standard.ods_fields:  # Check that all keys are provided for a rec and type is correct
            if key not in rec:
                self.qprint(f"{self.pre}Missing {key} {ending}")
                is_valid = False
            if rec[key] is not None:
                try:
                    _ = self.standard.ods_fields[key](rec[key])
                except ValueError:
                    self.qprint(f"{self.pre}{rec[key]} is wrong type for {key} {ending}")
                    is_valid = False
        for key in self.standard.time_fields:
            try:
                _ = Time(rec[key])
            except ValueError:
                self.qprint(f"{self.pre}{rec[key]} is not a valid astropy.time.Time input format {ending}")
                is_valid = False
        return is_valid

    def ods(self, ods):
        """
        Checks the ods records are correct and complete.

        Attributes
        ----------
        self.valid_records : list
            List of valid record entries in the list
        self.number_of_records : int
            Number of records checked.

        """
        valid_records = []
        for ctr, rec in enumerate(ods):
            is_valid = self.record(rec, ctr)
            if is_valid:
                valid_records.append(ctr)
        return valid_records
    
    def observation(self, rec, el_lim_deg=10.0, dt_sec=120.0, show_plot=False):
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

        Return
        ------
        tuple or False
            False if never above the horizon, otherwise a tuple containing the limiting times within the record span.

        """
        from astropy.coordinates import EarthLocation, AltAz, SkyCoord
        import astropy.units as u
        from numpy import where

        start = Time(rec[self.standard.start])
        stop = Time(rec[self.standard.stop])
        dt = TimeDelta(dt_sec, format='sec')
        times = []
        this_step = start
        while(this_step < stop):
            times.append(this_step)
            this_step += dt
        times = Time(times)
        location = EarthLocation(lat = float(rec[self.standard.lat]) * u.deg, lon = float(rec[self.standard.lon]) * u.deg, height = float(rec[self.standard.ele]) * u.m)

        aa = AltAz(location=location, obstime=times)
        coord = SkyCoord(float(rec[self.standard.ra]) * u.deg, float(rec[self.standard.dec]) * u.deg)
        obs = coord.transform_to(aa)
        above_horizon = where(obs.alt > el_lim_deg * u.deg)[0]
        if not len(above_horizon):
            return False
        if show_plot:
            import matplotlib.pyplot as plt
            plt.figure(self.standard.plot_azel)
            plt.plot(obs.az, obs.alt, label=rec[self.standard.source])
            plt.figure(self.standard.plot_timeel)
            plt.plot(times.datetime, obs.alt, label=rec[self.standard.source])
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
        from copy import copy
        entries = {}
        for i, rec in enumerate(ods):
            entries[(Time(rec[self.standard.start]).datetime, Time(rec[self.standard.stop]).datetime, i)] = i
        adjusted_entries = []
        for key in sorted(entries.keys()):
            adjusted_entries.append(copy(ods[entries[key]]))
        for i in range(len(adjusted_entries) - 1):
            this_stop = Time(adjusted_entries[i][self.standard.stop])
            next_start = Time(adjusted_entries[i+1][self.standard.start])
            if next_start < this_stop:  # Need to adjust
                if adjust == 'start':
                    next_start = this_stop + TimeDelta(time_offset_sec, format='sec')
                elif adjust == 'stop':
                    this_stop = next_start - TimeDelta(time_offset_sec, format='sec')
                adjusted_entries[i].update({self.standard.stop: this_stop.datetime.isoformat()})
                adjusted_entries[i+1].update({self.standard.start: next_start.datetime.isoformat()})
                if next_start < this_stop:
                    self.qprint(f"{self.pre}New start is before stop so still need to fix.")
        return adjusted_entries