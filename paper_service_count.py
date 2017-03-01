#!/usr/bin/env python

import argparse
import logging
import multiprocessing
import os
import sys
from argparse import RawTextHelpFormatter
from multiprocessing.pool import ThreadPool

import numpy as np

import offline.core.sla
from offline.tools.api import clean_and_create_experiment, create_sla, get_service_graph_generators, embbed_service

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


def unpack(first, *rest):
    return first, rest


def valid_topo(topo_spec):
    name, spec = unpack(*topo_spec.split(","))
    return (name, spec)


RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'offline/results')

logging.basicConfig(filename='simu.log', level="DEBUG", )

parser = argparse.ArgumentParser(description='1 iteration for solver', epilog=

""" Examples for different topologies:
    \t sudo docker run nherbaut/simuservice --start 0101 0202 0303 --cdn 0505 --vhg 1 --vcdn 1  --service_graph=powerlaw,n, m, p, seed, bw, delay, cpu\n
    \t sudo docker run nherbaut/simuservice --start 1 2 3 --cdn 93 --vhg 1 --vcdn 1 --service_graph=powerlaw,100,2,0.3,1,1000000000,20,200\n\n\n
    \t sudo docker run nherbaut/simuservice --start 0101 0202 0303 --cdn 0505 --vhg 1 --vcdn 1  --service_graph=erdos_renyi,n, p, seed, bw, delay, cpu\n
    \t sudo docker run nherbaut/simuservice --start 1 2 3 --cdn 10 --vhg 1 --vcdn 1 --service_graph=erdos_renyi,20,0.3,1,1000000000,20,200\n\n\n
    \t sudo docker run nherbaut/simuservice --start 0101 0202 0303 --cdn 0505 --vhg 1 --vcdn 1  --service_graph=grid,width, height, bw, delay, cpu\n
    \t sudo docker run nherbaut/simuservice --start 0101 0202 0303 --cdn 0505 --vhg 1 --vcdn 1 --service_graph=grid,5,5,1000000000,10,1000\n\n\n
    \t sudo docker run nherbaut/simuservice --start 22  --cdn 38 --vhg 1 --vcdn 1 --service_graph=file,file,cpu\n
    \t sudo docker run nherbaut/simuservice --start 22  --cdn 38 --vhg 1 --vcdn 1 --service_graph=file,Geant2012.graphml,10000


    """, formatter_class=RawTextHelpFormatter)
parser.add_argument("--disable-embedding", dest='disable_embedding',
                    help="disable the embedding, which cause the topology to be rendrered alone", action='store_true')
parser.add_argument('--sla_delay', help="delay toward TE, float in ms", default=30.0, type=float)
parser.add_argument('--max_start', type=int)

parser.add_argument('--max_cdn', type=int)

parser.add_argument('--vhg', type=int, help='vhg count (eg. 2)', default=None)
parser.add_argument('--seed', type=int, help='seed for random number generation', default=1)
parser.add_argument('--vcdn', type=int, help='vcdn count (eg. 1)', default=None)
parser.add_argument('--auto', dest='auto', action='store_true', help='automatic vhg vcdn count', default=False)

parser.add_argument('--vcdnratio', help="the share of source traffic toward vcdn (default 0.35)", default=0.35,
                    type=float)
parser.add_argument('--sourcebw', help="cumulated source bw from every source (default 100 bits) ", default=10000,
                    type=float)
parser.add_argument('--service_graph', help="specify service_graph to use", default=('grid', ["5", "5", "100000000", "10", "200"]),
                    type=valid_topo)

parser.add_argument('--plot', dest="plot", action="store_true")
parser.add_argument('--disable-heuristic', dest="disable_heuristic", action="store_true")
parser.add_argument('--disable-isomorph-check', dest="disable_isomorph_check", action="store_true")
parser.add_argument('--dest_folder', help="destination folder for restults", default=RESULTS_FOLDER)

args = parser.parse_args()
pool = ThreadPool(multiprocessing.cpu_count() - 1)
if args.auto is False and (args.vhg is None or args.vcdn is None):
    parser.error('please specify --vhg and --vcdn args if not automatic calculation')
elif args.auto is True and (args.vhg is not None or args.vcdn is not None):
    parser.error("can't specify vhg count of vcdn count in --auto mode")

res = np.zeros((args.max_start, args.max_cdn))
rs, su = clean_and_create_experiment(args.topo, args.seed)
for start in range(1, args.max_start + 1):
    for cdn in range(1, args.max_cdn + 1):
        candidates = []

        nodes_by_bw = su.get_nodes_by_bw()
        start_nodes = offline.core.sla.weighted_shuffle(list(nodes_by_bw.keys()), list(nodes_by_bw.values()), rs)[
                      -start:]

        nodes_by_degree = su.get_nodes_by_degree()
        cdn_nodes = offline.core.sla.weighted_shuffle(list(nodes_by_degree.keys()), list(nodes_by_degree.values()), rs)[
                    :cdn]

        sla = create_sla(start_nodes, cdn_nodes, args.sourcebw, su=su, rs=rs)

        candidates = get_service_graph_generators(sla,
                                                  automatic=True, use_heuristic=not args.disable_heuristic,
                                                  disable_isomorph_check=args.disable_isomorph_check)

        candidate_count = 0


        # sys.stdout.write("\n\t Embedding services:%d\n" % len(candidates_param))
        services = pool.map(embbed_service, candidates)

        res[start - 1, cdn - 1] += len(services)

np.savetxt(os.path.join(args.dest_folder, "res.txt"), res)
print(res)
print((np.sum(res)))
