Operational Data Sharing (ODS)

This reads, writes, updates and checks ODS lists.

ODS list are a list of ODS records.

An ODS file is a json file, with the the ODS list contained under the top-level key "ods_data"

Reading may come from an existing ODS file, from a datafile or be provided by a dictionary or Namespace.

Records read from a datafile or supplied, are appended to whatever ODS records are already contained in the class ODS list.
Reading an ODS file, will start a new/different class ODS list.

Files may be culled by provided a time (records ending before that time are removed) or by invalid (records not passed the checks are removed).

ODS checks are:
    1 - all supplied record entries have the right "name"
    2 - all entries are present and have the right type

The only method is "ods_engine" (from odsutils import ods_engine) and the only script is "odsuser.py".

Standard pip install.

The presumed workflow (as shown in odsuder.py and can be done in one call) is:
1 - read in an existing ODS file
2 - set the defaults you want (either a json file with default values or ':from_ods')
3 - add entries from a data file or can add on command line
4 - remove entries before a time (likely 'now')
5 - write the new ods file (give same filename to overwrite)

E.g.
odsuser.py -o ods_ata.json -d :from_ods -f obs.txt -i -t now -w ods_new.json
odsuser.py -d sites.json:ata -f obs.txt -i -t now -w ods_new.json

ACKNOWLEDGEMENTS
This software was developed with support from the National Science Foundation:
SII-NRDZ: Radio Astronomy Dynamic Satellite Inteference-Mitigation and Spectrum Sharing (RADYSISS) (AST-2232368)

The ODS system was developed by NRAO with support from the National Science Foundation's grants:
SII NRDZ: Dynamic Protection and Spectrum Monitoring for Radio Observatories (AST-2232159),
SWIFT-SAT: Observational Data Sharing (AST-2332422)