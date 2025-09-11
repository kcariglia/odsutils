from copy import copy
from .ods_check import ODSCheck
from . import ods_instance, logger_setup, __version__
from . import ods_tools as tools
from . import ods_timetools as timetools
import logging
from . import LOG_FILENAME, LOG_FORMATS

# Set up the logger
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

class ODS:
    """
    Utilities to handle ODS instances.

    The ODS instances are ods_instance.ODSInstance classes contained within the dictionary 'self.ods',
    each identified by a unique key (working_instance).  Unless a different instance is specified, the
    instance used is the one specified by 'self.working_instance, which is set to
    ods_instance.DEFAULT_WORKING_INSTANCE by default.

    The list of ODS records is stored in the 'entries' attribute of the ODSInstance class, and can be accessed
    using the 'self.ods[working_instance].entries' attribute.

    """
    def __init__(self, version='latest', working_instance=ods_instance.DEFAULT_WORKING_INSTANCE,
                 conlog='WARNING', filelog=False, **kwargs):
        """
        Parameters
        ----------
        version : str
            Version of default ODS standard -- note that instances can be different
        working_instance : str
            Key to use for the ods instance in use.
        conlog : str, False
            One of the logging levels for console: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
        filelog : str, False
            One of the logging levels for file: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
        **kwargs : kept to catch keywords
            'defaults' : dict, str, None

        """
        self.log_settings = logger_setup.Logger(logger, conlog=conlog, filelog=filelog, log_filename=LOG_FILENAME, path=None,
                                                filelog_format=LOG_FORMATS['filelog_format'], conlog_format=LOG_FORMATS['conlog_format'])
        logger.info(f"{__name__} ver. {__version__}")

        # ###
        self.version = version
        self.ods = {}
        self.defaults = {}
        self._flag_generate_instance_report = True
        self.new_ods_instance(working_instance, version=version, set_as_working=True)
        self.check = ODSCheck(alert=self.log_settings.conlog, standard=self.ods[working_instance].standard)
        if 'defaults' in kwargs:
            self.get_defaults(kwargs['defaults'])

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def post_ods(self, filename, instance_name='primary'):
        """
        Post (i.e. write) a given instance to a filename at path as an ODS json file.

        Parameters
        ----------
        filename : str
            ODS filename to write
        instance_name : str
            Name of instance to write, defaults to 'primary'

        """
        instance_name = self.get_instance_name(instance_name)
        if not self.ods[instance_name].number_of_records:
            logger.warning("Writing an empty ODS file!")
        self.ods[instance_name].write(filename)

    def assemble_ods(self, directory, post_to=None, initial_instance=None):
        """
        This will assemble an ODS file from all the files in a directory, culling duplicates and stale entries.
        It will initialize the assembled ODS with the initial_instance if provided.
        An empty one is created if none are found.

        New ODS instances are created for each file found, as well as one called 'assembly' for the
        assembled ODS.

        Parameters
        ----------
        directory : str
            Directory to search for ODS files (if a json filename is specified, will use its directory)
        post_to : str, None
            If not None, post the assembled ODS to this filename.
        initial_instance : str, None
            If not None, use this instance to initialize the assembled ODS.
            
        """
        from glob import glob
        import os.path as op
        if directory.endswith('json'):
            directory = op.dirname(directory)
        assembly_instance_name = 'assembly'
        ods_files = glob(op.join(directory, 'ods_*.json'))
        logger.info(f"Found {len(ods_files)} ODS files in {directory}.")
        self.new_ods_instance(instance_name=assembly_instance_name)
        if initial_instance is not None:
            if initial_instance in self.ods:
                self.merge(from_ods=initial_instance, to_ods=assembly_instance_name)
            else:
                logger.warning(f"Initial instance {initial_instance} not found -- starting with empty ODS.")
        for ods_file in ods_files:
            self.new_ods_instance(instance_name=ods_file)
            self.add(ods_file, instance_name=ods_file)
            self.merge(from_ods=ods_file, to_ods=assembly_instance_name)

        self.cull_by_time('now', 'stale', instance_name=assembly_instance_name)
        self.cull_by_duplicate(instance_name=assembly_instance_name)

        if post_to is not None:
            # Post the assembled ODS to an ODS file
            self.post_ods(post_to, instance_name=assembly_instance_name)
            logger.info(f"Posted assembled ODS to {post_to}")

    def new_ods_instance(self, instance_name, version='latest', set_as_working=False, overwrite=False):
        """
        Create a blank ODS instance and optionally set as the working instance.

        Parameters
        ----------
        instance_name : str
            Name of instance.
        version : str
            Standard version to use.
        set_as_working : bool
            Flag to reset the working_instance to this instance_name.

        """
        if instance_name in self.ods.keys():
            logger.warning(f"ODS instance {instance_name} already exists.")
            if not overwrite:
                return
            else:
                logger.info(f"Overwriting ODS instance {instance_name}.")
        self.ods[instance_name] = ods_instance.ODSInstance(
            instance_name = instance_name,
            version = version
        )
        if set_as_working:
            self.update_working_instance_name(instance_name)
    
    def update_working_instance_name(self, instance_name):
        """
        Update the class working_instance instance_name.
        
        Parameter
        ---------
        instance_name : str
            Name of instance

        """
        if instance_name in self.ods.keys():
            self.working_instance = instance_name
            logger.info(f"The ODS working instance is {self.working_instance}")
        else:
            logger.warning(f"ODS instance {instance_name} does not exist.")

    def get_instance_name(self, instance_name=None):
        """
        Return the class instance instance_name to use.
      
        Parameter
        ---------
        instance_name : str
            Name of instance

        Returns
        -------
        The instance name to use.
    
        """
        if instance_name is None:
            return self.working_instance
        if instance_name in self.ods:
            return instance_name
        logger.error(f"{instance_name} does not exist -- try making it with self.new_ods_instance or providing a different instance_name.")

    def instance_report(self, instance_name=None):
        instance_name = self.get_instance_name(instance_name)
        number_of_invalid_records = len(self.ods[instance_name].invalid_records)
        if self.ods[instance_name].number_of_records and number_of_invalid_records == self.ods[instance_name].number_of_records:
            logger.warning(f"All records ({self.ods[instance_name].number_of_records}) were invalid.")
        elif number_of_invalid_records:
            logger.warning(f"{number_of_invalid_records} / {self.ods[instance_name].number_of_records} were not valid.")
            for ctr, msg in self.ods[instance_name].invalid_records.items():
                logger.warning(f"Entry {ctr}:  {', '.join(msg)}")
        else:
            logger.info(f"{self.ods[instance_name].number_of_records} are all valid.")

    def get_defaults(self, defaults, version='latest'):
        """
        This takes in any of the same inputs as self.add() to populate the self.defaults dictionary.  It selects all of the entry sets with a length of 1.

        Parameter
        ---------
        defaults : any of
            ods record default values (keys are standard.ods_fields)
            - dict provides the actual default key/value pairs
            - str 
              (a) if starts with ':', uses "special case" of the from_ods input sets (can add options...)
              (b) is a filename with the defaults as a json
                  if there is a ':', then it is that filename preceding and the key after the :
        version : str
            Standard version to use.

        Attribute
        ---------
        defaults : dict
            Dictionary containing whatever ods records defaults are provided.
        new_ods_instance : creates a new instance called '__defaults__' to hold the defaults input

        """
        self.new_ods_instance('__defaults__', version=version, set_as_working=False, overwrite=True)
        if defaults is None:
            return
        self._flag_generate_instance_report = False
        self.add(defaults, instance_name='__defaults__', remove_duplicates=False)
        self.ods['__defaults__'].gen_info()
        self.defaults = copy(self.ods['__defaults__'].input_set_len_1)  # Cryptic, but means all entries with only one record in the set
        logger.info(f"Default values from {defaults}:")
        for key, val in self.defaults.items():
            logger.info(f"\t{key:26s}  {val}")
        self._flag_generate_instance_report = True

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
        self.read_ods(url, instance_name='from_web')
        self.cull_by_time(instance_name='from_web', cull_by='inactive')

        self.new_ods_instance('from_log')
        self.add_from_file(logfile, instance_name='from_log', sep=sep)
        self.merge('from_web', 'from_log', remove_duplicates=True)

        self.ods['from_log'].export2file(logfile, cols=cols, sep=sep)

    def check_active(self, ctime='now', read_from="https://www.seti.org/sites/default/files/HCRO/ods.json"):
        """Check which entry is active at ctime, if any."""
        self.new_ods_instance(instance_name='check_active')
        if isinstance(read_from, str):
            self.add(read_from, instance_name='check_active')
        else:
            logger.info("Not reading new ODS instance for check_active.")
        ctime = timetools.interpret_date(ctime, fmt='Time')
        active = []
        for i, entry in enumerate(self.ods['check_active'].entries):
            if entry['src_start_utc'] <= ctime <= entry['src_end_utc']:
                active.append(i)
        return active


    ##############################################MODIFY#########################################
    # Methods that modify the existing self.ods

    def update_entry(self, entry_num, updates, instance_name=None):
        """
        Update the entry number with the updates dict values.

        Parameters
        ----------
        entry_num : int
            Number of entry to update
        updates : dict
            Dictionary containing the updates
        instance_name : str, None
            Instance to update

        """
        instance_name = self.get_instance_name(instance_name)
        n_updates = self.ods[instance_name].update_entry(entry_num, updates)
        logger.info(f"Updated {instance_name} entry {entry_num} with {n_updates} changes.")

    def update_by_elevation(self, el_lim_deg=10.0, dt_sec=120, instance_name=None, show_plot=False):
        """
        Check an ODS for sources above an elevation limit.  Will update the times for those above that limit.

        Parameters
        ----------
        el_lim_deg : float
            Elevation limit to use, in degrees.
        dt_sec : float
            Time step to use for check, in seconds.
        instance_name : str, None
            Name of instance to use
        show_plot : bool
            Flag to show a plot.

        """
        instance_name = self.get_instance_name(instance_name)
        logger.info(f"Updating {instance_name} for el limit {el_lim_deg}")
        updated_ods = []
        for rec in self.ods[instance_name].entries:
            time_limits = self.check.observation(rec, el_lim_deg=el_lim_deg, dt_sec=dt_sec, show_plot=show_plot)
            if time_limits and len(time_limits):
                valid_rec = copy(rec)
                valid_rec.update({self.ods[instance_name].standard.start: time_limits[0], self.ods[instance_name].standard.stop: time_limits[1]})
                updated_ods.append(valid_rec)
        self.ods[instance_name].entries = updated_ods
        self.ods[instance_name].gen_info()
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

    def update_by_continuity(self, time_offset_sec=1, adjust='start', instance_name=None):
        """
        Check the ODS for time continuity.  Not checked yet.

        Parameters
        ----------
        time_offset_set : int/float
            Spacing between record times.
        adjust : str
            Side to adjust start/stop
        instance_name : str, None
            Name of instance to use

        """
        instance_name = self.get_instance_name(instance_name)
        self.ods[instance_name].entries = self.check.continuity(self.ods[instance_name], time_offset_sec=time_offset_sec, adjust=adjust)
        self.ods[instance_name].gen_info()

    def update_ods_times(self, times=None, start=None, obs_len_sec=None, instance_name=None):
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
        instance_name : str, None
            Name of instance to use

        """
        instance_name = self.get_instance_name(instance_name)
        if times is not None:
            if len(times) != self.ods[instance_name].number_of_records:
                logger.warning("times list doesn't have the right number of entries")
                return
        elif start is None or obs_len_sec is None:
            logger.warning("haven't specified enough parameters.")
            return
        else:
            if not isinstance(obs_len_sec, list):
                obs_len_sec = [obs_len_sec] * self.ods[instance_name].number_of_records
            elif len(obs_len_sec) != self.ods[instance_name].number_of_records:
                logger.warning("obs_len_sec doesn't have the right number of entries")
                return
            times = tools.generate_observation_times(start, obs_len_sec)
        for i, tt in enumerate(times):
            this_update = {self.ods[instance_name].standard.start: tt[0],
                           self.ods[instance_name].standard.stop: tt[1]}
            self.ods[instance_name].entries[i].update(this_update)
        self.ods[instance_name].gen_info()

    def cull_by_time(self, cull_time='now', cull_by='stale', instance_name=None):
        """
        Remove entries with end times before cull_time.  Overwrites self.ods[instance_name]

        Parameter
        ---------
        cull_time : str
            isoformat time string
        cull_for : str
            Either 'stale' or 'active'
        instance_name : str or None
            ODS instance

        """
        if cull_by not in ['stale', 'inactive']:
            logger.warning(f"Invalid cull parameter: {cull_by}")
            return
        instance_name = self.get_instance_name(instance_name)
        cull_time = timetools.interpret_date(cull_time, fmt='Time')
        logger.info(f"Culling ODS for {cull_time} by {cull_by}")
        culled_ods = []
        for rec in self.ods[instance_name].entries:
            stop_time = rec[self.ods[instance_name].standard.stop]
            add_it = True
            if cull_time > stop_time:
                add_it = False
            elif cull_by == 'inactive':
                start_time = rec[self.ods[instance_name].standard.start]
                if cull_time < start_time:
                    add_it = False
            if add_it:
                culled_ods.append(rec)
        self.ods[instance_name].entries = copy(culled_ods)
        self.ods[instance_name].gen_info()
        logger.info(f"retaining {len(self.ods[instance_name].entries)} of {self.ods[instance_name].number_of_records}")

    def cull_by_invalid(self,  instance_name=None):
        """
        Remove entries that fail validity check.

        Parameter
        ---------
        instance_name : str, None
            Name of instance to use

        """
        instance_name = self.get_instance_name(instance_name)
        self.ods[instance_name].gen_info()
        logger.info("Culling ODS for invalid records.")
        if not len(self.ods[instance_name].valid_records):
            logger.info("retaining all.")
            return
        starting_number = copy(self.ods[instance_name].number_of_records)
        culled_ods = []
        for irec in self.ods[instance_name].valid_records:
            culled_ods.append(copy(self.ods[instance_name].entries[irec]))
        self.ods[instance_name].entries = culled_ods
        self.ods[instance_name].gen_info()
        if not self.ods[instance_name].number_of_records:
            logger.warning("Retaining no records.")
        else:
            logger.info(f"retaining {self.ods[instance_name].number_of_records} of {starting_number}")
    
    def cull_by_duplicate(self, instance_name=None):
        """
        Remove duplicate entries, sorts it by the standard.sort_order_time

        """
        instance_name = self.get_instance_name(instance_name)
        logger.info("Culling ODS for duplicates")
        starting_number = len(self.ods[instance_name].entries)
        self.ods[instance_name].sort()
        if len(self.ods[instance_name].entries) == starting_number:
            logger.info("retaining all.")
            return
        self.ods[instance_name].gen_info()
        logger.info(f"retaining {self.ods[instance_name].number_of_records} of {starting_number}")

    def update_instance_meta(self, instance_name=None):
        """
        Update the metadata for a specific instance.

        Parameter
        ---------
        instance_name : str or None
            Name of instance to use

        """
        instance_name = self.get_instance_name(instance_name)
        self.ods[instance_name].gen_info()
        self.instance_report(instance_name=instance_name)

    ##############################################ADD############################################
    # Methods that add to the existing self.ods
    def new_record(self, **kwargs):
        """
        Append a new record to self.ods[instance_name] with kwargs.

        This is usually called by self.add().

        """
        instance_name = self.get_instance_name(kwargs['instance_name'] if 'instance_name' in kwargs else None)
        self.ods[instance_name].new_record(kwargs, defaults=self.defaults)

    def add(self, inp, **kwargs):
        """
        Appends a new ods record to self.ods[instance_name].entries.

        Parameters
        ----------
        inp : dict, list of dicts, or object with attributes, or filename
            Input record(s) to add

        Optional keywords
        -----------------
        instance_name : str, None
            Name of instance to use
        remove_duplicates : bool
            Flag to cull duplicates after adding

        """
        if inp is None:  # Nothing will happen.
            return
        instance_name = kwargs['instance_name'] if 'instance_name' in kwargs else None
        if isinstance(inp, dict):
            self.new_record(**inp, instance_name=instance_name)
        elif isinstance(inp, list):
            remove_duplicates = kwargs['remove_duplicates'] if 'remove_duplicates' in kwargs else True
            self._flag_generate_instance_report = False
            for rec in inp:
                self.add(rec, **kwargs)
            self._flag_generate_instance_report = True
            if remove_duplicates:
                self.cull_by_duplicate(instance_name=instance_name)
        elif isinstance(inp, str):
            self._add_from_file(inp, **kwargs)
        else:
            try:
                data = vars(inp)
                data.update({'instance_name': instance_name})
                self.new_record(**data)
            except:
                logger.warning("Not a valid input type.")
                return
        if self._flag_generate_instance_report:
            self.update_instance_meta(instance_name=instance_name)

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
        self.add(self.ods[from_ods].entries, instance_name=to_ods, remove_duplicates=remove_duplicates)

    def _add_from_file(self, data_file_name, instance_name=None, sep='auto', replace_char=None, header_map=None, remove_duplicates=True):
        """
        Append new records from a json file or a data file assuming the first line is a header.

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
        instance_name = self.get_instance_name(instance_name)

        if data_file_name.startswith('http'):
            ods_input = tools.get_url(data_file_name, fmt='json')
        elif data_file_name.endswith('.json'):
            ods_input = tools.read_json_file(data_file_name)
        else:
            obs_list = tools.read_data_file(data_file_name, sep=sep, replace_char=replace_char, header_map=header_map)#, instance_name=instance_name)
            ods_input = []
            for _, row in obs_list.iterrows():
                ods_input.append(row.to_dict())
        if isinstance(ods_input, dict) and self.ods[instance_name].standard.data_key in ods_input:
                ods_input = ods_input[self.ods[instance_name].standard.data_key]               
        self.add(ods_input, instance_name=instance_name, remove_duplicates=remove_duplicates)

    ######################################OUTPUT##################################
    # Methods that show/save_to_file ods instance

    def view_ods(self, order=['src_id', 'src_start_utc', 'src_end_utc'], number_per_block=5, instance_name=None):
        """
        View the ods as a table arranged in blocks.

        Parameters
        ----------
        order : list
            First entries in table, rest of ods record values are append afterwards.
        number_per_block : int
            Number of records to view per block

        """
        instance_name = self.get_instance_name(instance_name)
        if not self.ods[instance_name].number_of_records:
            logger.info("No records to print.")
            return
        print(self.ods[instance_name].view(order=order, number_per_block=number_per_block))
    
    def graph_ods(self, numpoints=160, instance_name=None):
        """
        Text-based graph of ods times/targets.

        """
        instance_name = self.get_instance_name(instance_name)
        if not self.ods[instance_name].number_of_records:
            logger.info("No records to graph.")
            return
        self.ods[instance_name].graph(numpoints=numpoints)

    def plot_ods_coverage(self, instance_name=None, log=False):
        import matplotlib.pyplot as plt

        instance_name = self.get_instance_name(instance_name)
        self.cov_Tot, self.cov_times = self.check.coverage(self.ods[instance_name])
        for xx, yy in self.cov_times:
            plt.plot([xx, yy], [0, 0], lw=5)
        if log:
            self.check.read_log_file(log)
            from numpy import zeros
            ticks = zeros(len(self.check.log_data.keys()))
            plt.plot(self.check.log_data.keys(), ticks, 'k|', markersize=15)

    def export2file(self, file_name, instance_name=None, sep=','):
        """
        Export the ods instance to a data file.

        Parameters
        ----------
        file_name : str
            Name of data file
        instance_name : str or None
            ODS instance
        sep : str
            Separator to use

        """
        instance_name = self.get_instance_name(instance_name)
        if not self.ods[instance_name].number_of_records:
            logger.warning("Writing an empty ODS file!")
        self.ods[instance_name].export2file(file_name, sep=sep)