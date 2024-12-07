from .ods_tools import Base


class ODSCheck(Base):
    """
    Utilities to check ODS records.

    """

    def __init__(self, standard):
        self.standard = standard

    def record(self, rec, ctr=None):
        """
        Checks a single ods record for:
            1 - keys are all valid ODS fields
            2 - values are all consistent with ODS field type
            3 - all fields are present

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
                self.qprint(f"{key} not an ods_field {ending}")
                is_valid = False
            elif rec[key] is None:
                self.qprint(f"Value for {key} is None {ending}")
                is_valid = False
        for key in self.standard.ods_fields:  # Check that all keys are provided for a rec and type is correct
            if key not in rec:
                self.qprint(f"Missing {key} {ending}")
                is_valid = False
            if rec[key] is not None:
                try:
                    _ = self.standard.ods_fields[key](rec[key])
                except ValueError:
                    self.qprint(f"{rec[key]} is wrong type for {key} {ending}")
                    is_valid = False
        return is_valid

    def ods(self, ods):
        """
        Checks the ods records that they are correct and complete.

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
    
    def observation(self, rec, ctr=None, number_times=10):
        from astropy.time import Time
        from astropy.coordinates import EarthLocation, AltAz, SkyCoord
        import astropy.units as u

        start = Time(rec[self.standard.start])
        stop = Time(rec[self.standard.stop])
        dt = (stop - start) / (number_times - 1)
        times = []
        for i in range(number_times):
            times.append(start + i * dt)
        times = Time(times)
        location = EarthLocation(lat = float(rec[self.standard.lat]) * u.deg, lon = float(rec[self.standard.lat]) * u.deg, height = float(rec[self.standard.ele]) * u.m)

        aa = AltAz(location=location, obstime=times)
        coord = SkyCoord(float(rec[self.standard.ra]) * u.deg, float(rec[self.standard.dec]) * u.deg)
        obs = coord.transform_to(aa)
        print(obs)