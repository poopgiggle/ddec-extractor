#!/usr/bin/env python2

import data_defs

f = open('hard-brake.bin','rb')
message = f.read()

parsed_data = data_defs.parse_message(message)
