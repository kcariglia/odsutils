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

The ODS system was developed by NRAO with support from the National Science Foundation's grants:
SII NRDZ: Dynamic Protection and Spectrum Monitoring for Radio Observatories (AST-2232159),
SWIFT-SAT: Observational Data Sharing (AST-2332422)