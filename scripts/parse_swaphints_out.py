#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

import sys
import struct



def status(i):
  error = {
     1: 'RECLAIMED',
     0: 'reclaim_page failed',
    -21: 'ERR_SWAPHINTS_ISOLATE_LRU',
    -27: 'ERR_SWAPHINTS_UNEVICTABLE',
    -101: 'ERR_SWAPHINTS_NOT_PAGELRU',
    -102: 'ERR_SWAPHINTS_PAGETRANSCOMPOUND',
    -103: 'ERR_SWAPHINTS_MAPCOUNT'
  }
  return error.get(i, "UNKNOWN-{}".format(i))





with open(sys.argv[1], 'rb') as f:
  data = f.read()

print("pfn, status")

out = {}
outr = {}

i = 0
for statusi, retries, pfn in struct.iter_unpack('iiQ',data):
  #print("statusi {}  retries {}  pfn {}".format(statusi, retries, pfn))
  s = status(statusi)
  if out.get(s, None) is None:
    out[s] = {}
  if out[s].get(pfn, None) is None:
    out[s][pfn] = 0
  out[s][pfn] += 1
  if outr.get(retries, None) is None:
    outr[retries] = 0
  outr[retries] += 1
  i += 1

pfns = {}
for s in out:
  p = len(out[s])
  print('{}:\t{}'.format(p,s))
  for pfn in out[s]:
    if pfns.get(pfn,None) is None:
      pfns[pfn] = 0
    pfns[pfn] += 1

print('{}:\tentry count'.format(i))

print('retries, count')
for r in sorted(outr.keys()):
  print("{},{}\n".format(r,outr[r]))
