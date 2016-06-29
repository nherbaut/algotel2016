#!/usr/bin/env python

import argparse
import os

import pickle
import sys

import numpy as np


from ..core.service import Service
from ..core.sla import generate_random_slas
from ..core.solver import solve
from ..core.substrate import Substrate
from offline.core.sla import Sla
GEANT_PATH=os.path.join(os.path.dirname(os.path.realpath(__file__)),'../data/Geant2012.graphml')


def valid_grid(gridspec):
    try:
        grid=[int(x) for x in gridspec.split("x")]
        if len(grid)!=2:
            raise ValueError
        else:
            return grid

    except ValueError:
        msg = "Not a valid grid: '{0}', should axb with a,b > 0 .".format(gridspec)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(description='1 iteration for solver')
parser.add_argument('-t', "--topo", dest='topo', action='store_true')
parser.add_argument('--vhg', help="the number of failure until the algorithm stops", default=1,type=int)
parser.add_argument('--vcdn', help="number of VCDN", default=1,type=int)
parser.add_argument('--sla_delay', help="delay toward vCDN", default=30.0,type=float)
parser.add_argument('--start', metavar='S', type=str, nargs='+',
                    help='a list of starters')
parser.add_argument('--cdn', metavar='CDN', type=str, nargs='+',
                    help='a list of CDN')

parser.add_argument('--vcdnratio', help="the share of source traffic toward vcdn", default=0.35,type=float)
parser.add_argument('--sourcebw', help="cumulated source bw from every source", default=1000000000,type=int)
parser.add_argument('--grid', help="Start from a new substrate", default=None, type=valid_grid)


args = parser.parse_args()





rs = np.random.RandomState()
if args.grid is not None:
    x,y=args.grid
    su=Substrate.fromSpec(x,y,10**10,1,100)
else:
    su = Substrate.fromGraph(rs, GEANT_PATH)


if args.topo:
    su.write()
    exit(0)


for s in args.start:
    assert s in su.nodesdict , "%s not in %s" % (s,su.nodesdict.keys())

for s in args.cdn:
    assert s in su.nodesdict

su.write()

service=Service(args.sourcebw, args.vhg, args.sla_delay, args.vcdnratio, 5, 3, args.vcdn, args.start,
                 args.cdn, len(args.cdn), True)
service.write()


mapping = solve(service, su,preassign_vhg=True)

if not mapping is None:

    su.consume_service(service, mapping)
    su.write()
    mapping.save()
    # os.remove("service.pickle")
    sys.stdout.write("success: %e\n" % mapping.objective_function)
    exit(0)
else:
    sys.stdout.write("failure\n")
    # mapping = solve(service, su,allow_violations=True)
    # if mapping:
    #    for index, violation in enumerate(mapping.violations,start=1):
    #        print("violation %d : %s" % (index,violation))
    exit(1)
