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

i = 0
for statusi, pfn in struct.iter_unpack('qQ',data):
  s = status(statusi)
  if out.get(s, None) is None:
    out[s] = {}
  if out[s].get(pfn, None) is None:
    out[s][pfn] = 0
  out[s][pfn] += 1
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
