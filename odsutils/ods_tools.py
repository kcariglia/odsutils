import json
from astropy.time import Time


def read_json_file(file_name):
    """
    Read a json file.
    
    Parameter
    ---------
    file_name : str
        Name of file to read

    Return
    ------
    dict : file contents

    """
    if not filename.endswith('.json'):
        filename = filename + '.json'
    with open(filename, 'r') as fp:
        input_file = json.load(fp)
    return input_file


def write_json_file(file_name, payload, indent=2):
    """
    Write a json file.
    
    Parameters
    ----------
    file_name : str
        Name of file to write.
    payload : dict
        Data to write.
    indent : int
        Indent to use.

    """
    with open(file_name, 'w') as fp:
        json.dump(payload, fp, indent=indent)


def read_data_file(file_name, sep='auto', replace_char=None, header_map=None):
    """
    Read a data file - assumes a header row.
    
    Parameters
    ----------
    file_name : str
        Name of file to read.
    sep : str
        Data separator in file, if 'auto' will check header row.
    replace : dict, list, str or None
        In the header will replace the character key with the dict value in case 'escape' characters.
        List will convert to {[0]: [1]}
        Str will convert to list, then if list above or len == 1 {[0]: ''}
    header_map : None or dict
        If dict, will rename the header columns.

    Returns
    -------
    pandas dataFrame

    """
    import pandas as pd

    if sep == 'auto':
        with open(file_name, 'r') as fp:
            header = fp.readline()
        for s in [',', '\t', ' ', ';']:
            if s in header:
                sep = s
                break

    data = pd.read_csv(file_name, sep=sep, skipinitialspace=True)

    if replace_char is not None:
        if not isinstance(replace_char, dict):
            replace_char = listify(replace_char)
            if len(replace_char) == 1:
                replace_char.append('')
            if len(replace_char) == 2:
                replace_char = {replace_char[0]: replace_char[1]}
            else:  # Not allowed.
                replace_char = {}
        for key, val in replace_char.items():
            data.columns = data.columns.str.replace(key, val)
    if header_map is not None:
        if isinstance(header_map, str):
            header_map = read_json_file(header_map)
        data = data.rename(header_map, axis='columns')

    return data


def write_data_file(file_name, ods, cols, sep=','):
    """
    Parameters
    file_name : str
        Name of output file
    ods : list of dict
        List if dictionaries comprising ODS entries
    cols : list or dict
        Columns to output
    sep : str
        Separator to use, if 'auto' will use ','

    """
    if sep == 'auto':
        sep = ','
    with open(file_name, 'w') as fp:
        print(sep.join(cols), file=fp)
        for rec in ods:
            row = []
            for key in cols:
                row.append(str(rec[key]))
            print(sep.join(row), file=fp)


def get_json_url(url):
    """
    Read a json url.

    Parameter
    ---------
    url : str
        String with the URL.

    Return
    ------
    dict : url json data

    """
    import requests

    try:
        xxx = requests.get(url)
    except Exception as e:
        print(f"Error reading {url}:  {e}")
        return
    return xxx.json()


def listify(x, d={}, sep=','):
    """
    Convert input to list.

    Parameters
    ----------
    x : *
        Input to listify
    d : dict
        Default/other values for conversion.
    sep : str
        Separator to use if str
    
    Return
    ------
    list : converted x (or d[x])

    """
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str) and x in d:
        return d[x]
    if isinstance(x, str):
        if sep == 'auto':
            sep = ','
        return x.split(sep)
    return [x]


def make_time(t):
    """
    Parameter
    ---------
    t : anything parseable by astropy.time.Time or 'now'

    Return
    ------
    astropy.time.Time

    """
    if t == 'now':
        return Time.now()
    try:
        return Time(t)
    except ValueError:
        print("NEED TO DO SOME CHECKING, E.G. timezone aware etc")
        raise ValueError(f"Error in make_time {t}")

def time2str(t):
    """
    Parameter
    ---------
    t : Time
        time to convert

    Return
    ------
    str : isoformat string

    """
    if isinstance(t, str):
        return t
    return t.datetime.isoformat(timespec='seconds')


def sort_entries(ods, terms, collapse=False, reverse=False):
    """
    Sort the ods records with the supplied list of terms (keys in the record) -- the position number is last
    to make sure there is a unique key unless collapse is True

    Parameters
    ----------
    ods : list of dict
        A list of dictionaries with the records.
    terms : list
        The list of dictionary keys upon which to sort.
    collapse : bool
        Flag to leave off unique position number term
    reverse : bool
        Flag to reverse sort

    Return
    ------
    Sorted version of the input list.

    """
    from copy import copy

    entries = {}
    for i, rec in enumerate(ods):
        sort_key = []
        for key in terms:
            sort_key.append(str(rec[key]))
        if not collapse:
            sort_key.append(i)
        sort_key = tuple(sort_key)
        entries[sort_key] = i
    adjusted_entries = []
    for key in sorted(entries.keys(), reverse=reverse):
        adjusted_entries.append(copy(ods[entries[key]]))
    return adjusted_entries


def generate_observation_times(start, obs_len_sec, gap=1.0, N=None):
    """
    Generate a list of start/stop times.

    Parameters
    ----------
    start : something for make_time
        starting time
    obs_len_sec : float/int or list
        length of observation(s), if list, must equal. If not, N must be set
    gap : float/int
        Gap in seconds between observations, default to 1s.

    Return
    ------
    list : start/stop times

    """
    from copy import copy
    from astropy.time import TimeDelta
    times = []
    start = make_time(start)
    if not isinstance(obs_len_sec, list):
        obs_len_sec = [obs_len_sec] * N
    current = start
    for obs in obs_len_sec:
        stop = current + TimeDelta(obs, format='sec')
        times.append([copy(current), copy(stop)])
        current += TimeDelta(obs+gap, format='sec')
    return times