#!/usr/bin/env python2
import json
import base64
import data_defs

f = open('ddec1587-ft-lauderdale.json','r')
data_dict = json.load(f)

for key in data_dict.keys():
    print("Parsing %s" % key)
    this_page = data_dict[key]
    raw_page = base64.b64decode(this_page)
    print(data_defs.parse_message(raw_page))
