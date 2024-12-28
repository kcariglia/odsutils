from copy import copy
from .ods_standard import Standard
from . import ods_tools as tools
from numpy import floor


DEFAULT_WORKING_INSTANCE = 'primary'
PLOT_AZEL = 'Az vs El'
PLOT_TIMEEL = 'Time vs El'
REF_LATEST_TIME = '2026-12-31T23:59'
REF_EARLIEST_TIME = '2020-01-01T00:00'


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
        self.standard = Standard(version=version)
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
        self.earliest = tools.make_time(REF_LATEST_TIME)
        self.latest = tools.make_time(REF_EARLIEST_TIME)
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
            header = ['Field    \    #'] + [str(i) for i in blk]
            data = []
            for key in order:
                row = [key] + [self.entries[i][key] for i in blk]
                data.append(row)
            tble = tabulate(data, headers=header)
            print(tble)
            print('=' * len(tble.splitlines()[1]))
    
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

    def export2file(self, filename, cols='all', sep=','):
        """
        Export the ods to a data file.

        Parameters
        ----------
        file_name : str
            Name of data file
        cols : str ('all', csv-list) or list
            List of entry keys
        sep : str
            Separator to use

        """
        self.convert_time_to_str()
        cols = list(self.standard.ods_fields.keys()) if cols == 'all' else cols = tools.listify(cols)
        tools.write_data_file(filename, self.entries, cols, sep=sep)
