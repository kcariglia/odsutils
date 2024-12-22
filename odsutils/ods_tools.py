import json


def read_json_file(filename):
    if not filename.endswith('.json'):
        filename = filename + '.json'
    with open(filename, 'r') as fp:
        input_file = json.load(fp)
    return input_file


def write_json_file(file_name, payload, indent=2):
    with open(file_name, 'w') as fp:
        json.dump(payload, fp, indent=indent)


def read_data_file(file_name, sep='\s+', replace_char=None, header_map=None):
    import pandas as pd

    data = pd.read_csv(file_name, sep=sep, skipinitialspace=True)

    if replace_char is not None:
        if isinstance(replace_char, str):
            replace_char = replace_char.split(',')
        if len(replace_char) == 1:
            replace_char.append('')
        data.columns = data.columns.str.replace(replace_char[0], replace_char[1])
    if header_map is not None:
        if isinstance(header_map, str):
            header_map = read_json_file(header_map)
        data = data.rename(header_map, axis='columns')

    return data


def write_data_file(file_name, ods, cols, sep=' '):
    with open(file_name, 'w') as fp:
        print(sep.join(cols), file=fp)
        for rec in ods:
            row = []
            for key in cols:
                row.append(str(rec[key]))
            print(sep.join(row), file=fp)


def get_json_url(url):
    import requests

    try:
        xxx = requests.get(url)
    except Exception as e:
        print(f"Error reading {url}:  {e}")
        return
    return xxx.json()


def make_time(t):
    """
    Parameter
    ---------
    t : anything parseable by astropy.time.Time or 'now'

    Return
    ------
    astropy.time.Time

    """
    from astropy.time import Time
    if t == 'now':
        return Time.now()
    try:
        return Time(t)
    except ValueError:
        print("NEED TO DO SOME CHECKING, E.G. timezone aware etc")
        raise ValueError(f"Error in make time {t}")


def sort_entries(ods, terms):
    """
    Sort the ods records with the supplied list of terms (keys in the record) -- the position number is last
    to make sure there is a unique key.

    Parameters
    ----------
    ods : list of dict
        A list of dictionaries with the records.
    terms : list
        The list of dictionary keys upon which to sort.

    Return
    ------
    Sorted version of the input list.

    """
    from copy import copy

    entries = {}
    for i, rec in enumerate(ods):
        sort_key = []
        for key in terms:
            sort_key.append(rec[key])
        sort_key.append(i)
        sort_key = tuple(sort_key)
        entries[sort_key] = i
    adjusted_entries = []
    for key in sorted(entries.keys()):
        adjusted_entries.append(copy(ods[entries[key]]))
    return adjusted_entries


def generate_observation_times(start, obs_len_sec):
    from astropy.time import TimeDelta
    times = []
    start = make_time(start)
    current = start
    for obs in obs_len_sec:
        stop = current + TimeDelta(obs, format='sec')
        times.append([current, stop])
        current += TimeDelta(obs+1, format='sec')
    return times


class Base:
    def qprint(self, msg, end='\n'):
        if msg.startswith("ERROR:"):
            raise ValueError(msg)
        if not hasattr(self, 'quiet'):
            self.quiet = False
        if not self.quiet or msg.startswith("WARNING:"):
            print(msg, end=end)