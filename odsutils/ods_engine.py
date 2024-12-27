from copy import copy
from . import ods_standard
from .ods_check import ODSCheck
from . import ods_tools as tools
from . import __version__
from numpy import floor
import logging
import warnings
from erfa import ErfaWarning
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=ErfaWarning)


logger = logging.getLogger(__name__)

class ODSInstance:
    """Light class containing the data, some core classes and metadata -- most handling is done within ODS."""

    def __init__(self, name, version='latest'):
        """
        Parameters
        ----------
        name : str
            Name of instance -- the key used in ODS
        version : str
            Standard version to use.

        """
        self.name = name
        self.standard = ods_standard.Standard(version=version)
        self.input = 'init'
        self.entries = []
        self.valid_records = []
        self.invalid_records = {}
        self.number_of_records = 0
        self.input_sets = {'invalid': set()}
        self.time_format = 'string'

    def new_record(self, entry={}, defaults={}):
        """
        Add a new record, with each value set to None, then apply defaults, then new fields and append to entries.

        Parameter
        ---------
        defaults : dict
            Dictionary containing default values
        fields : dict
            Dictionary containing new fields.

        """
        rec = {}
        for key in self.standard.ods_fields:
            rec[key] = None
            if key in entry:
                rec[key] = copy(entry[key])
            elif key in defaults:
                rec[key] = copy(defaults[key])
        self.entries.append(rec)

    def read(self, ods_input):
        """
        Read in an existing ods file or dictionary and pull out input sets.

        Checking is done in ODS (arguably should probably be done here)

        Parameter
        ---------
        ods_input : str or dict
            Name of ods json file or dict

        Attributes
        ----------
        input : str
            The supplied ods file name or source
        entries : list
            List of ods records that is manipulated
        number_of_records : int
            Number of records in ods instance
        input_sets : set
            List of input sets and invalid keys -- set in gen_info
        number_of_records : int
            Number of records (entries) -- set in gen_info

        """
        if isinstance(ods_input, dict):
            input_ods_data = copy(ods_input)
            self.input = 'dictionary'
        elif isinstance(ods_input, str):
            input_ods_data = tools.read_json_file(ods_input)
            self.input = ods_input 
        else:
            return False
        self.entries += input_ods_data[self.standard.data_key]  # This is the internal list of ods records
        self.gen_info()
        self.time_format = 'string'
        return True

    def gen_info(self):
        """
        Get some extra info on the instance.

        Attributes
        ----------
        valid_records : list
            List of valid record entry numbers
        invalid_record : dict
            Dict of invalid records, keyed on entry number
        input_sets : set
            List of input sets and invalid keys -- set in gen_info
        number_of_records : int
            Number of records (entries) -- set in gen_info
        earliest : Time
            Time of earliest record
        latest : Time
            Time of latest record

        """
        self.make_time()
        self.earliest = tools.make_time(ods_standard.REF_LATEST_TIME)
        self.latest = tools.make_time(ods_standard.REF_EARLIEST_TIME)
        self.number_of_records = len(self.entries)
        self.invalid_records = {}
        self.valid_records = []
        for ctr, entry in enumerate(self.entries):
            for key, val in entry.items():
                if key in self.standard.ods_fields:
                    self.input_sets.setdefault(key, set())
                    self.input_sets[key].add(val)
                    if key == self.standard.start and entry[key] < self.earliest:
                        self.earliest = copy(entry[key])
                    elif key == self.standard.stop and entry[key] > self.latest:
                        self.latest = copy(entry[key])
                else:
                    self.input_sets['invalid'].add(key)
            is_valid, msg = self.standard.valid(entry)
            if is_valid:
                self.valid_records.append(ctr)
            else:
                self.invalid_records[ctr] = msg

    def make_time(self):
        """
        Make Time attributes for time fields -- it modifies the instance.

        """
        if self.time_format == 'time':  # Already is
            return
        self.time_format = 'time'
        for entry in self.entries:
            for key in self.standard.time_fields:
                entry[key] = tools.make_time(entry[key])

    def convert_time_to_str(self):
        """
        This is the inverse of make_time -- it modifies the instance.

        """
        if self.time_format == 'string':  # Already is
            return
        self.time_format = 'string'
        for entry in self.entries:
            for key in self.standard.time_fields:
                entry[key] = tools.time2str(entry[key])

    def view(self, order=['src_id', 'src_start_utc', 'src_end_utc'], number_per_block=5):
        """
        View the ods instance as a table arranged in blocks.

        Parameters
        ----------
        order : list
            First entries in table, rest of ods record values are appended afterwards.
        number_per_block : int
            Number of records to view per block

        """
        if not self.number_of_records:
            return
        from tabulate import tabulate
        from numpy import ceil
        self.convert_time_to_str()
        blocks = [range(i * number_per_block, (i+1) * number_per_block) for i in range(int(ceil(self.number_of_records / number_per_block)))]
        blocks[-1] = range(blocks[-1].start, self.number_of_records)
        order = order + [x for x in self.standard.ods_fields if x not in order]
        for blk in blocks:
            data = []
            for key in order:
                row = [key] + [self.entries[i][key] for i in blk]
                data.append(row)
            print(tabulate(data))
    
    def graph(self, numpoints=160, numticks=10):
        """
        Text-based graph of ods times/targets sorted by start/stop times.

        Parameters
        ----------
        numpoints : int
            Number of points to use.
        numticks : int
            Number of interior ticks -- not used yet.

        """
        self.make_time()
        sorted_ods = tools.sort_entries(self.entries, [self.standard.start, self.standard.stop], collapse=False, reverse=False)
        #dticks = ((self.latest - self.earliest) / (numticks + 2)).to('second').value  # Not used yet.

        dt = ((self.latest - self.earliest) / numpoints).to('second').value
        rows = []
        for rec in sorted_ods:
            rows.append(rec[self.standard.source])
        stroff = max([len(x) for x in rows]) + 1

        start_label, stop_label = f"{self.earliest.datetime.isoformat(timespec='seconds')}", f"{self.latest.datetime.isoformat(timespec='seconds')}"
        current = int((tools.make_time('now') - self.earliest).to('second').value / dt)
        show_current = True if (current > -1 and current < numpoints) else False
        len_label = len(start_label)
        stroff = max(stroff, len_label // 2 + 1)
        spaces = ' ' * (stroff - 1 - len_label // 2), ' ' * (numpoints-len_label-1)
        labelrow = f"{spaces[0]}{start_label}{spaces[1]}{stop_label}"
        tickrow = [' '] * (stroff) + ['|'] + [' '] * (numpoints-2) + ['|']
        if show_current:
            tickrow[current + stroff] = '0'
        tickrow = ''.join(tickrow)
        dashrow = '-' * (stroff + numpoints + len_label//2)
        graphhdr = f"-- GRAPH: {self.name} --\n"
        print(f"{dashrow}\n{graphhdr}\n{labelrow}\n{tickrow}")
        for rec in sorted_ods:
            row = ['.'] * numpoints
            starting = int(floor((rec[self.standard.start]  -  self.earliest).to('second').value / dt))
            ending = int(floor((rec[self.standard.stop] - self.earliest).to('second').value / dt)) + 1
            for star in range(starting, ending):
                try:
                    row[star] = '*'
                except IndexError:
                    pass
            if show_current:
                row[current] = 'X' if row[current] == '*' else '|'
            print(f"{rec[self.standard.source]:{stroff}s}{''.join(row)}")
        print(f"{tickrow}\n{labelrow}\n{dashrow}")

    def write(self, file_name):
        """
        Export the ods instance to an ods json file.

        Parameter
        ---------
        file_name : str
            Name of ods json file to write

        """
        self.convert_time_to_str()
        tools.write_json_file(file_name, {self.standard.data_key: self.entries})

    def export2file(self, filename, sep=','):
        """
        Export the ods to a data file.

        Parameters
        ----------
        file_name : str
            Name of data file
        sep : str
            Separator to use

        """
        self.convert_time_to_str()
        tools.write_data_file(filename, self.entries, self.standard.ods_fields, sep=sep)

class ODS:
    """
    Utilities to handle ODS instances.

    Maintains an internal self.ods[<working_instance>] ods record list that gets manipulated.
    Adding the <working_instance> allows for flexibility, however generally one will only make/use one key denoted 'primary'.

    """
    def __init__(self, version='latest', working_instance=ods_standard.DEFAULT_WORKING_INSTANCE, output='INFO'):
        """
        Parameters
        ----------
        version : str
            Version of default ODS standard -- note that instances can be different
        working_instance : str
            Key to use for the ods instance in use.
        output : str
            One of the logging levels 'DEBUG', 'INFO', 'WARNING', 'ERROR'

        """
        # All this seems to be needed.
        level = getattr(logging, output.upper())
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        logger.addHandler(ch)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        # ###
        self.version = version
        self.working_instance = working_instance
        self.reset_ods_instances('all', version=version)
        self.defaults = {}
        self.check = ODSCheck(alert=output, standard=self.ods[working_instance].standard)

        logger.info(f"{__name__} ver. {__version__}")

    def reset_ods_instances(self, instances='all', version='latest'):
        """
        Resets the internal instance(s).

        Parameters
        ----------
        instances : str, list
            Instances to reset -- 'all'/list/csv-list
        version : str
            Standard version oto use

        """
        if instances == 'all':
            self.ods = {}
            self.ods_instance(name=self.working_instance, version=version)
            return
        for name in tools.listify(instances):
            if name in self.ods:
                self.ods[name] = self.ods_instance(name=name, version=version)
            else:
                logger.warning(f"{name} is not an instance.")

    def ods_instance(self, name, version='latest', set_as_working=False):
        """
        Create a blank ODS instance and optionally set as the working instance.

        Parameters
        ----------
        name : str
            Name of instance.
        version : str
            Standard version to use.
        set_as_working : bool
            Flag to reset the working_instance to this name.

        """
        if name in self.ods:
            logger.warning(f"{name} already exists -- try self.reset_ods_instances")
            return
        self.ods[name] = ODSInstance(
            name = name,
            version = version
        )
        if set_as_working:
            self.update_working_instance(name)
    
    def update_working_instance(self, name):
        """
        Update the class working_instance name.
        
        Parameter
        ---------
        name : str
            Name of instance

        """
        self.working_instance = name
        logger.info(f"The new ODS working instance is {self.working_instance}")

    def get_instance_name(self, name=None):
        """
        Return the class instance name to use.
      
        Parameter
        ---------
        name : str
            Name of instance

        Returns
        -------
        The instance name to use.
    
        """
        if name is None:
            return self.working_instance
        if name in self.ods:
            return name
        logger.error(f"{name} does not exist -- try making it with self.ods_instance")

    def read_ods(self, ods_input, name=None):
        """
        Read in ods data from a file or input dictionary in same format.

        Parameters
        ----------
        ods_input : str
            ODS input, either filename or dictionary.
        name : str, None
            Name of instance to use

        """
        name = self.get_instance_name(name)
        self.ods[name].read(ods_input)
        logger.info(f"Read {self.ods[name].number_of_records} records from {self.ods[name].input}")
        self.instance_report(name=name)

    def instance_report(self, name=None):
        name = self.get_instance_name(name)
        number_of_invalid_records = len(self.ods[name].invalid_records)
        if self.ods[name].number_of_records and number_of_invalid_records == self.ods[name].number_of_records:
            logger.error(f"All records ({self.ods[name].number_of_records}) were invalid.")
        elif number_of_invalid_records:
            logger.warning(f"{number_of_invalid_records} / {self.ods[name].number_of_records} were not valid.")
            for ctr, msg in self.ods[name].invalid_records.items():
                logger.warning(f"Entry {ctr}:  {', '.join(msg)}")
        else:
            logger.info(f"{self.ods[name].number_of_records} are all valid.")

    def get_defaults_dict(self, defaults='from_ods'):
        """
        Parameter
        ---------
        defaults : dict, str, None
            ods record default values (keys are standard.ods_fields)
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
            self.defaults = copy(defaults)
            defaults = 'input_dict'
        elif isinstance(defaults, str):
            if '.json' in defaults:
                fnkey = defaults.split(':')
                self.defaults = tools.read_json_file(fnkey[0])
                if len(fnkey) == 2:
                    self.defaults = self.defaults[fnkey[1]]
            elif defaults == 'from_ods':  # The only option for now, uses single-valued keys
                self.defaults = {}
                for key, val in self.ods[self.working_instance].input_sets.items():
                    if key != 'invalid' and len(val) == 1:
                        self.defaults[key] = list(val)[0]
            else:
                logger.error(f"Not valid default case: {defaults}")

        logger.info(f"Default values from {defaults}:")
        for key, val in self.defaults.items():
            logger.info(f"\t{key:26s}  {val}")

    def online_ods_monitor(self, url="https://www.seti.org/sites/default/files/HCRO/ods.json", logfile='online_ods_mon.txt', sep=','):
        """
        Checks the online ODS URL against a local log to update for active records.  Typically used in a crontab to monitor
        the active ODS records posted.

        Parameters
        ----------
        url : str
            URL of online ODS server
        logfile : str
            Local logfile to use.

        """
        self.ods_instance('from_web')
        self.read_ods(tools.get_json_url(url), name='from_web')
        self.cull_by_time(name='from_web', cull_by='inactive')

        self.ods_instance('from_log')
        self.add_from_file(logfile, name='from_log', sep=sep)
        self.merge('from_web', 'from_log', remove_duplicates=True)

        self.ods['from_log'].export2file(logfile, sep=sep)

    ##############################################MODIFY#########################################
    # Methods that modify the existing self.ods

    def update_entry(self, entry, updates, name=None):
        """
        Update the entry number with the updates dict values.

        Parameters
        ----------
        entry : int
            Number of entry to update
        updates : dict
            Dictionary containing the updates
        name : str, None
            Instance to update

        """
        name = self.get_instance_name(name)
        if isinstance(entry, int):
            self.ods[name].entries[entry].update(updates)
        else:
            logger.info('No other update entry options.')
            return
        self.ods[name].gen_info()

    def update_by_elevation(self, el_lim_deg=10.0, dt_sec=120, name=None, show_plot=False):
        """
        Check an ODS for sources above an elevation limit.  Will update the times for those above that limit.

        Parameters
        ----------
        el_lim_deg : float
            Elevation limit to use, in degrees.
        dt_sec : float
            Time step to use for check, in seconds.
        name : str, None
            Name of instance to use
        show_plot : bool
            Flag to show a plot.

        """
        name = self.get_instance_name(name)
        updated_ods = []
        for rec in self.ods[name].entries:
            time_limits = self.check.observation(rec, el_lim_deg=el_lim_deg, dt_sec=dt_sec, show_plot=show_plot)
            if time_limits:
                valid_rec = copy(rec)
                valid_rec.update({self.ods[name].standard.start: time_limits[0], self.ods[name].standard.stop: time_limits[1]})
                updated_ods.append(valid_rec)
        self.ods[name].entries = updated_ods
        self.ods[name].gen_info()
        if show_plot:
            import matplotlib.pyplot as plt
            plt.figure(ods_standard.PLOT_AZEL)
            plt.xlabel('Azimuth [deg]')
            plt.ylabel('Elevation [deg]')
            plt.axis(ymin = el_lim_deg)
            plt.legend()
            plt.figure(ods_standard.PLOT_TIMEEL)
            plt.xlabel('Time [UTC]')
            plt.ylabel('Elevation [deg]')
            plt.axis(ymin = el_lim_deg)
            plt.legend()

    def update_by_continuity(self, time_offset_sec=1, adjust='start', name=None):
        """
        Check the ODS for time continuity.  Not checked yet.

        Parameters
        ----------
        time_offset_set : int/float
            Spacing between record times.
        adjust : str
            Side to adjust start/stop
        name : str, None
            Name of instance to use

        """
        name = self.get_instance_name(name)
        self.ods[name].entries = self.check.continuity(self.ods[name], time_offset_sec=time_offset_sec, adjust=adjust)
        self.ods[name].gen_info()

    def update_ods_times(self, times=None, start=None, obs_len_sec=None, name=None):
        """
        Reset the src_start_utc and src_stop_utc fields in self.ods.

        Parameter
        ---------
        times : list of lists/None or None
            If not None, each list item contains new start/stop for that record in the list or skip if None.
            Must be len(self.ods)
        start : str
            Start time in isoformat or 'now'
        obs_len_sec : str, list or None
            If 'start' is not None, this is the length/observation
            If list, must be len(self.ods)
        name : str, None
            Name of instance to use

        """
        name = self.get_instance_name(name)
        if times is not None:
            if len(times) != self.ods[name].number_of_records:
                logger.warning("times list doesn't have the right number of entries")
                return
        elif start is None or obs_len_sec is None:
            logger.warning("haven't specified enough parameters.")
            return
        else:
            if not isinstance(obs_len_sec, list):
                obs_len_sec = [obs_len_sec] * self.ods[name].number_of_records
            elif len(obs_len_sec) != self.ods[name].number_of_records:
                logger.warning("obs_len_sec doesn't have the right number of entries")
                return
            times = tools.generate_observation_times(start, obs_len_sec)
        for i, tt in enumerate(times):
            this_update = {self.ods[name].standard.start: tt[0].datetime.isoformat(timespec='seconds'),
                           self.ods[name].standard.stop: tt[1].datetime.isoformat(timespec='seconds')}
            self.ods[name].entries[i].update(this_update)

    def cull_by_time(self, cull_time='now', cull_by='stale', name=None):
        """
        Remove entries with end times before cull_time.  Overwrites self.ods[name]

        Parameter
        ---------
        cull_time : str
            isoformat time string
        cull_for : str
            Either 'stale' or 'active'
        name : str or None
            ODS instance

        """
        if cull_by not in ['stale', 'inactive']:
            logger.error(f"Invalid cull parameter: {cull_by}")
        name = self.get_instance_name(name)
        cull_time = tools.make_time(cull_time)
        logger.info(f"Culling ODS for {cull_time} by {cull_by}")
        self.ods[name].make_time()
        culled_ods = []
        for rec in self.ods[name].entries:
            stop_time = rec[self.ods[name].standard.stop]
            add_it = True
            if cull_time > stop_time:
                add_it = False
            elif cull_by == 'inactive':
                start_time = rec[self.ods[name].standard.start]
                if cull_time < start_time:
                    add_it = False
            if add_it:
                culled_ods.append(rec)
        self.ods[name].entries = copy(culled_ods)
        self.ods[name].gen_info()
        logger.info(f"retaining {len(self.ods[name].entries)} of {self.ods[name].number_of_records}")

    def cull_by_invalid(self,  name=None):
        """
        Remove entries that fail validity check.

        Parameter
        ---------
        name : str, None
            Name of instance to use

        """
        name = self.get_instance_name(name)
        self.ods[name].gen_info()
        logger.info("Culling ODS for invalid records.")
        if not len(self.ods[name].valid_records):
            logger.info("retaining all.")
            return
        starting_number = copy(self.ods[name].number_of_records)
        culled_ods = []
        for irec in self.ods[name].valid_records:
            culled_ods.append(copy(self.ods[name].entries[irec]))
        self.ods[name].entries = culled_ods
        self.ods[name].gen_info()
        if not self.ods[name].number_of_records:
            logger.warning("Retaining no records.")
        else:
            logger.info(f"retaining {self.ods[name].number_of_records} of {starting_number}")
    
    def cull_by_duplicate(self, name=None):
        """
        Remove duplicate entries, sorts it by the standard.sort_order_time

        """
        name = self.get_instance_name(name)
        self.ods[name].convert_time_to_str()
        logger.info("Culling ODS for duplicates")
        starting_number = len(self.ods[name].entries)
        self.ods[name].entries = tools.sort_entries(self.ods[name].entries, self.ods[name].standard.sort_order_time, collapse=True, reverse=False)
        if len(self.ods[name].entries) == starting_number:
            logger.info("retaining all.")
            return
        self.ods[name].gen_info()
        logger.info(f"retaining {self.ods[name].number_of_records} of {starting_number}")


    ##############################################ADD############################################
    # Methods that add to the existing self.ods

    def add_new_record(self, name=None, **kwargs):
        """
        Append a new record to self.ods.

        """
        name = self.get_instance_name(name)
        self.ods[name].new_record(kwargs, defaults=self.defaults)
        self.ods[name].gen_info()
        self.instance_report(name=name)

    def add_from_namespace(self, ns, name=None):
        """
        Appends a new ods record to self.ods supplied as a Namespace

        """
        self.add_new_record(name=name, **vars(ns))

    def merge(self, from_ods, to_ods=ods_standard.DEFAULT_WORKING_INSTANCE, remove_duplicates=True):
        """
        Merge two ODS instances.

        Parameters
        ----------
        from_ods : str
            Name of ODS instance entries to be merged
        to_ods : str
            Name of ODS instance to be the merged ODS
        remove_duplicates : bool
            Flag to purge merged ODS of duplicates

        """
        logger.info(f"Updating {to_ods} from {from_ods}")
        self.add_from_list(self.ods[from_ods].entries, name=to_ods, remove_duplicates=remove_duplicates)

    def add_from_list(self, entries, name=None, remove_duplicates=True):
        """
        Append a records to self.ods[name], using defaults then entries.
        
        Parameters
        ----------
        entries : list of dicts
            List of dictionaries containing ODS fields

        """
        name = self.get_instance_name(name)
        for entry in entries:
            self.ods[name].new_record(entry, defaults=self.defaults)
        logger.info(f"Read {len(entries)} records from list.")
        if remove_duplicates:
            self.cull_by_duplicate(name=name)
        self.ods[name].gen_info()
        self.instance_report(name=name)

    def add_from_file(self, data_file_name, name=None, sep='auto', replace_char=None, header_map=None, remove_duplicates=True):
        """
        Append new records from a data file to self.ods; assumes the first line is a header.

        Parameters
        ----------
        data_file_name : str
            Name of input data file.
        sep : str
            separator
        replace_char : None, str, tuple, list
            replace characters in column headers
            - str: remove that character (replace with '')
            - tuple/list of length 1: same as above
            - tuple/list of length 2: replace [0] with [1]
        header_map : None, dict, str
            replace column header names with those provided
            - str: read json file
            - dict: {<ods_header_name>: <datafile_header_name>}

        """
        name = self.get_instance_name(name)
        self.data_file_name = data_file_name
        obs_list = tools.read_data_file(self.data_file_name, sep=sep, replace_char=replace_char, header_map=header_map)
        for _, row in obs_list.iterrows():
            self.ods[name].new_record(row.to_dict(), defaults=self.defaults)
        logger.info(f"Read {len(obs_list.index)} records from {self.data_file_name}.")
        if remove_duplicates:
            self.cull_by_duplicate(name=name)
        self.ods[name].gen_info()
        self.instance_report(name=name)

    ######################################OUTPUT##################################
    # Methods that show/save ods instance

    def view_ods(self, order=['src_id', 'src_start_utc', 'src_end_utc'], number_per_block=5, name=None):
        """
        View the ods as a table arranged in blocks.

        Parameters
        ----------
        order : list
            First entries in table, rest of ods record values are append afterwards.
        number_per_block : int
            Number of records to view per block

        """
        name = self.get_instance_name(name)
        if not self.ods[name].number_of_records:
            logger.info("No records to print.")
            return
        self.ods[name].view(order=order, number_per_block=number_per_block)
    
    def graph_ods(self, numpoints=160, name=None):
        """
        Text-based graph of ods times/targets.

        """
        name = self.get_instance_name(name)
        if not self.ods[name].number_of_records:
            logger.info("No records to graph.")
            return
        self.ods[name].graph(numpoints=numpoints)

    def plot_ods_coverage(self, name=None, starting='start', stopping='stop', time_step_min=1.0):
        from numpy import array
        import matplotlib.pyplot as plt

        name = self.get_instance_name(name)
        t, c = self.check.coverage(self.ods[name], starting=starting, stopping=stopping, time_step_min=time_step_min)
        c = array(c)
        print(f"{100 * c.sum() / len(c): .1f}% of the period is covered.")
        plt.plot(t, c)
        plt.show()

    def write_ods(self, file_name, name=None):
        """
        Export the ods to an ods json file.

        Parameters
        ----------
        file_name : str
            Name of ods json file to write
        name : str or None
            ODS instance

        """
        name = self.get_instance_name(name)
        if not self.ods[name].number_of_records:
            logger.warning("Writing an empty ODS file!")
        self.ods[name].write(file_name)

    def write_file(self, file_name, name=None, sep=','):
        """
        Export the ods to a data file.

        Parameters
        ----------
        file_name : str
            Name of data file
        name : str or None
            ODS instance
        sep : str
            Separator to use

        """
        name = self.get_instance_name(name)
        if not self.ods[name].number_of_records:
            logger.warning("Writing an empty ODS file!")
        self.ods[name].export2file(file_name, sep=sep)