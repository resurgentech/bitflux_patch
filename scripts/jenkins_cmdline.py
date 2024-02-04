#!/usr/bin/python3
import json
import yaml
import sys
import re

##########################################################################
## Jenkins logs spit out the cmdline it executes wrong.
##  This will transform it into something you can run.

infilename = sys.argv[1]

with open(infilename, "r") as file:
	data = file.read()

output = {}

print(data)
print()
b = data.split('./build.py ')
cmd = "./build.py \\\n"
c = b[1].split('--')

for a in c:
	print(a)
	print()
	b = re.match("(\w+)\s+(.*)",a)
	if b:
		c = b.groups()
		print("\t{}".format(c[0]))
		print()
		print("\t\t{}".format(c[1]))
		print()
		output[c[0]] = c[1]

print()

settings = json.dumps(output['settings'])
output['settings'] = settings

print(output)
print()
print()
for k,v in output.items():
	cmd += "\t--{} {} \\\n".format(k,v)


print(cmd)
