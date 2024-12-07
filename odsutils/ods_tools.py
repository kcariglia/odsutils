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


class Base:
    def qprint(self, msg, end='\n'):
        if not self.quiet or msg.startswith("WARNING:"):
            print(msg, end=end)