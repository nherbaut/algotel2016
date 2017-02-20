#!/usr/bin/env python

import itertools
import logging
import multiprocessing
import os
import sys
import time
from multiprocessing.pool import ThreadPool

from numpy.random import RandomState

from ..core.service import Service
from ..core.service_topo_generator import ServiceTopoFullGenerator
from ..core.service_topo_heuristic import ServiceTopoHeuristic
from ..core.sla import Sla, SlaNodeSpec
from ..core.substrate import Substrate
from ..time.persistence import Session, Base, engine, drop_all, Tenant, Node

GEANT_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/Geant2012.graphml')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../results')

candidate_count = 0


def clean_and_create_experiment(topo, seed):
    '''

    :param topo: the topology generated according to specs
    :param seed: the randomset used for generation
    :return: rs, substrate
    '''

    session = Session()
    Base.metadata.create_all(engine)
    drop_all()

    rs = RandomState(seed)
    su = Substrate.fromSpec(topo, rs)
    return rs, su


def embbed_service(x):
    session = Session()
    #print("%d so far " % candidate_count)

    topology, slasIDS, vhg_count, vcdn_count, use_heuristic = x
    service = Service(topo_instance=topology, slasIDS=slasIDS, vhg_count=vhg_count,
                      vcdn_count=vcdn_count, use_heuristic=use_heuristic)
    session.add(service)
    session.flush()
    global candidate_count
    candidate_count += 1

    return service


def create_sla(starts, cdns, sourcebw, topo=None, su=None, rs=None, seed=0):
    if su is None:
        rs, su = clean_and_create_experiment(topo, seed)

    nodes_names = [n.name for n in su.nodes]
    session = Session()

    for s in starts:
        assert s in nodes_names, "%s not in %s" % (s, nodes_names)

    if len(cdns) == 1 and cdns[0] == "all":
        cdns = [node.name for node in su.nodes]

    for s in cdns:
        assert s in nodes_names, "%s not in %s" % (s, nodes_names)

    su.write(RESULTS_FOLDER)
    session.add(su)
    session.flush()

    tenant = Tenant()
    session.add(tenant)

    sla_node_specs = []
    bw_per_s = sourcebw / float(len(starts))
    for start in starts:
        ns = SlaNodeSpec(topoNode=session.query(Node).filter(Node.name == start).one(), type="start",
                         attributes={"bandwidth": bw_per_s})
        sla_node_specs.append(ns)

    for cdn in cdns:
        ns = SlaNodeSpec(topoNode=session.query(Node).filter(Node.name == cdn).one(), type="cdn",
                         attributes={"bandwidth": 1})
        sla_node_specs.append(ns)

    sla = Sla(substrate=su, delay=200, max_cdn_to_use=1, tenant_id=tenant.id, sla_node_specs=sla_node_specs)
    session.add(sla)
    session.flush()

    return sla


def generate_candidates_param(sla, vhg_count=None, vcdn_count=None,
                              automatic=True, use_heuristic=True, disable_isomorph_check=True):
    pool = ThreadPool(multiprocessing.cpu_count() - 1)

    topoContainers=[]
    if not automatic:
        if use_heuristic:
            topoContainer = ServiceTopoHeuristic(sla=sla, vhg_count=vhg_count, vcdn_count=vcdn_count)
        else:
            topoContainer = ServiceTopoFullGenerator(sla=sla, vhg_count=vhg_count, vcdn_count=vcdn_count,
                                                     disable_isomorph_check=disable_isomorph_check)

        for topo in topoContainer.getTopos():
            yield (topo, [sla.id], vhg_count, vcdn_count, use_heuristic)
    else:
        merged_sla = Service.get_merged_sla([sla])

        for vhg_count in range(1, len(merged_sla.get_start_nodes()) + 1):
            for vcdn_count in range(1, vhg_count + 1):
                if use_heuristic:
                    topoContainer = ServiceTopoHeuristic(sla=merged_sla, vhg_count=vhg_count, vcdn_count=vcdn_count)
                else:
                    topoContainer = ServiceTopoFullGenerator(sla=merged_sla, vhg_count=vhg_count, vcdn_count=vcdn_count,
                                                             disable_isomorph_check=disable_isomorph_check)

                for topo in topoContainer.getTopos():
                    yield (topo, [merged_sla.id], vhg_count, vcdn_count, use_heuristic)


def optimize_sla(sla, vhg_count=None, vcdn_count=None,
                 automatic=True, use_heuristic=True):
    candidates_param = generate_candidates_param(sla, vhg_count=vhg_count, vcdn_count=vcdn_count,
                                                 automatic=automatic, use_heuristic=use_heuristic)

    # sys.stdout.write("\n\t Service to embed :%d\n" % len(candidates_param))

    # print("%d param to optimize" % len(candidates_param))
    pool = ThreadPool(multiprocessing.cpu_count() - 1)
    # sys.stdout.write("\n\t Embedding services:%d\n" % len(candidates_param))

    #services = pool.map(embbed_service, candidates_param)


    services = [embbed_service(param) for param in candidates_param]
    sys.stdout.write(" done!\n")

    services = filter(lambda x: x.mapping is not None, services)
    services = sorted(services, key=lambda x: x.mapping.objective_function, )

    for service in services:
        logging.debug(
            "%d %lf %d %d" % (service.id, service.mapping.objective_function, service.vhg_count, service.vcdn_count))

    if len(services) > 0:
        winner = services[0]
        return winner, candidate_count
    else:
        raise ValueError("failed to compute valide mapping")
