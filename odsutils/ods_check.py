from . import ods_tools as tools
from astropy.time import TimeDelta
import logging


logger = logging.getLogger(__name__)


class ODSCheck:
    """
    Utilities to check ODS instances/records.

    """
    def __init__(self, alert='INFO', standard=None):
        """
        Parameter
        ---------
        alert : str
            Default alert

        """
        # All this seems to be needed.
        level = getattr(logging, alert.upper())
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        logger.addHandler(ch)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        #
        self.standard = standard

    def update_standard(self, standard):
        self.standard = standard
    
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
        if not len(times):
            return times
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
            logger.warning(f'Invalid adjust spec - {adjust}')
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
                    logger.warning(f"{self.pre}New start is before stop so still need to fix.")
        return adjusted_entries

    def coverage(self, ods, starting, stopping, time_step_min=1):
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
        from copy import copy

        ods.make_time()
        sorted_entries = tools.sort_entries(ods.entries, [ods.standard.stop, ods.standard.start])
        dt = TimeDelta(time_step_min * 60.0, format='sec')
        starting = ods.earliest if starting == 'start' else tools.make_time(starting)
        stopping = ods.latest if stopping == 'stop' else tools.make_time(stopping)
        logger.info(f"Checking coverage from {starting} - {stopping}")
        this_time = copy(starting)
        ts = []
        covered = []
        starting_index = 0
        while this_time < stopping:
            ts.append(this_time.datetime)
            if this_time < ods.earliest or this_time > ods.latest:
                covered.append(0)
            else:
                for entry in sorted_entries[starting_index:]:
                    if this_time > entry[ods.standard.stop]:
                        starting_index += 1
                    if entry[ods.standard.start] <= this_time <= entry[ods.standard.stop]:
                        covered.append(1)
                        break
                else:
                    covered.append(0)
            this_time += dt
        return ts, covered