from copy import copy
from .ods_check import ODSCheck
from . import ods_instance
from . import ods_tools as tools
from . import __version__
import logging
from sys import stdout


logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')


class ODS:
    """
    Utilities to handle ODS instances.

    Maintains an internal self.ods[<working_instance>] ods record list that gets manipulated.
    Adding the <working_instance> allows for flexibility, however generally one will only make/use one key denoted 'primary'.

    """
    def __init__(self, version='latest', working_instance=ods_instance.DEFAULT_WORKING_INSTANCE, output='INFO', quiet=None):
        """
        Parameters
        ----------
        version : str
            Version of default ODS standard -- note that instances can be different
        working_instance : str
            Key to use for the ods instance in use.
        output : str
            One of the logging levels 'DEBUG', 'INFO', 'WARNING', 'ERROR'
        quiet : bool, None DEPRECATED
            Kept for backward compatibility.  Use output

        """
        if quiet is not None:
            output = 'ERROR' if quiet else 'INFO'
        console_handler = logging.StreamHandler(stdout)
        console_handler.setLevel(output.upper())
        console_handler.setFormatter(logging.Formatter("{levelname} - {message}", style='{'))
        logger.addHandler(console_handler)
        logger.info(f"{__name__} ver. {__version__}")

        # ###
        self.version = version
        self.working_instance = working_instance
        self.reset_ods_instances('all', version=version)
        self.defaults = {}
        self.check = ODSCheck(alert=output, standard=self.ods[working_instance].standard)

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
            self.new_ods_instance(name=self.working_instance, version=version)
            return
        for name in tools.listify(instances):
            if name in self.ods:
                self.ods[name] = self.new_ods_instance(name=name, version=version)
            else:
                logger.warning(f"{name} is not an instance.")

    def new_ods_instance(self, name, version='latest', set_as_working=False):
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
        self.ods[name] = ods_instance.ODSInstance(
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
        logger.error(f"{name} does not exist -- try making it with self.new_ods_instance or providing a different name.")

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
            logger.warning(f"All records ({self.ods[name].number_of_records}) were invalid.")
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
                logger.warning(f"Not valid default case: {defaults}")
                return

        logger.info(f"Default values from {defaults}:")
        for key, val in self.defaults.items():
            logger.info(f"\t{key:26s}  {val}")

    def online_ods_monitor(self, url="https://www.seti.org/sites/default/files/HCRO/ods.json", logfile='online_ods_mon.txt', cols='all', sep=','):
        """
        Checks the online ODS URL against a local log to update for active records.  Typically used in a crontab to monitor
        the active ODS records posted.

        Parameters
        ----------
        url : str
            URL of online ODS server
        logfile : str
            Local logfile to use.
        cols : str('all', csv-list) or list
            Columns to write out.
        sep : str
            Separator to use in file.

        """
        self.new_ods_instance('from_web')
        self.read_ods(tools.get_json_url(url), name='from_web')
        self.cull_by_time(name='from_web', cull_by='inactive')

        self.new_ods_instance('from_log')
        self.add_from_file(logfile, name='from_log', sep=sep)
        self.merge('from_web', 'from_log', remove_duplicates=True)

        self.ods['from_log'].export2file(logfile, cols=cols, sep=sep)

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
        logger.info(f"Updating {name} for el limit {el_lim_deg}")
        updated_ods = []
        for rec in self.ods[name].entries:
            time_limits = self.check.observation(rec, el_lim_deg=el_lim_deg, dt_sec=dt_sec, show_plot=show_plot)
            if time_limits and len(time_limits):
                valid_rec = copy(rec)
                valid_rec.update({self.ods[name].standard.start: time_limits[0], self.ods[name].standard.stop: time_limits[1]})
                updated_ods.append(valid_rec)
        self.ods[name].entries = updated_ods
        self.ods[name].gen_info()
        if show_plot:
            import matplotlib.pyplot as plt
            plt.figure(ods_instance.PLOT_AZEL)
            plt.xlabel('Azimuth [deg]')
            plt.ylabel('Elevation [deg]')
            plt.axis(ymin = el_lim_deg)
            plt.legend()
            plt.figure(ods_instance.PLOT_TIMEEL)
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
            logger.warning(f"Invalid cull parameter: {cull_by}")
            return
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

    def merge(self, from_ods, to_ods=ods_instance.DEFAULT_WORKING_INSTANCE, remove_duplicates=True):
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