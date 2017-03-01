import os
import re
import subprocess

from jinja2 import Environment, PackageLoader
from sqlalchemy import or_, and_
from sqlalchemy.orm.exc import NoResultFound

from ..core.mapping import Mapping
from ..time.persistence import Session, Edge, ServiceEdge, ServiceNode, NodeMapping, EdgeMapping, Node

OPTIM_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../optim')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../results')
PRICING_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../pricing')

env = Environment(loader=PackageLoader("offline", 'optim'))
template_optim = env.get_template('optim.zpl.tpl')
# template_optim_slow = env.get_template('optim-slow.zpl.tpl')
template_optim_slow = env.get_template('optim.zpl.tpl')
template_optim_debug = env.get_template('batch-debug.sh')


class Solver(object):
    def __solve_inplace(self, allow_violations=False, path=".", use_heuristic=True, reopt=False):
        '''
        __solve without rewriting intermedia files
        :return: a mapping
        '''
        if use_heuristic:
            optim_template = template_optim
        else:
            optim_template = template_optim_slow

        session = Session()
        if not os.path.exists(os.path.join(RESULTS_FOLDER, path)):
            os.makedirs(os.path.join(RESULTS_FOLDER, path))

        # copy template to target folder
        with open(os.path.join(RESULTS_FOLDER, path, "optim.zpl"), "w") as f:
            f.write(optim_template.render(dir=os.path.join(RESULTS_FOLDER, path), pricing_dir=PRICING_FOLDER))

        with open(os.path.join(RESULTS_FOLDER, path, "debug.sh"), "w") as f:
            f.write(template_optim_debug.render(dir=os.path.join(RESULTS_FOLDER, path), pricing_dir=PRICING_FOLDER))

        os.chmod(os.path.join(RESULTS_FOLDER, path, "debug.sh"), 0o711)

        violations = []
        if not allow_violations:
            if not reopt:  # run the optim without CDNs
                # print "optimize"
                subprocess.call(
                    ["scip", "-c", "read %s" % os.path.join(RESULTS_FOLDER, path, "optim.zpl"), "-c", "optimize ", "-c",
                     "write solution %s" % (os.path.join(RESULTS_FOLDER, path, "solutions.data")), "-c", "q"],
                    stdout=open(os.devnull, 'wb')
                )
            else:  # run the optim with CDN using reoptim
                # print "re-optimize"
                subprocess.call(["scip", "-c", "read %s" % os.path.join(RESULTS_FOLDER, path, "optim.zpl"), "-c",
                                 "read %s" % os.path.join(RESULTS_FOLDER, path, "solutions.data sol"), "-c",
                                 "set reoptimization enable true", "-c", "optimize ", "-c",
                                 "write solution %s" % (os.path.join(RESULTS_FOLDER, path, "solutions.data")), "-c",
                                 "q"],
                                stdout=open(os.devnull, 'wb')
                                )

        else:
            subprocess.call(
                ["scip", "-c", "read %s" % os.path.join(RESULTS_FOLDER, path, "optim.zpl"), "-c", "optimize ", "-c",
                 "write solution %s" % (os.path.join(RESULTS_FOLDER, path, "solutions.data")), "-c", "q"],
                stdout=open(os.devnull, 'wb')
            )
        # plotting.plotsol()
        # os.subprocess.call(["cat", "./substrate.dot", "|", "dot", "-Tpdf", "-osol.pdf"])
        with open(os.path.join(RESULTS_FOLDER, path, "solutions.data"), "r") as sol:
            data = sol.read()
            if "infeasible" in data or "no solution" in data:
                return None

            data = data.split("\n")
            nodesSols = []
            edgesSol = []
            objective_function = None
            for line in data:

                # search node
                matches = re.findall("^x\$(.*)\$([^ \t]+) +([^ \t]+)", line)
                if (len(matches) > 0):
                    try:
                        node = session.query(Node).filter(Node.name == matches[0][0]).one()
                        snode_id, service_id, sla_id = matches[0][1].split("_")
                        value = matches[0][2]
                        service_node_id = session.query("ServiceNode.id").filter(
                            and_(ServiceNode.sla_id == sla_id, ServiceNode.service_id == service_id,
                                 ServiceNode.name == snode_id)).one()[0]
                        nodeMapping = NodeMapping(node_id=node.id, service_node_id=service_node_id,
                                                  service_id=service_id,
                                                  sla_id=sla_id)
                        nodesSols.append(nodeMapping)

                        continue
                    except NoResultFound as e:
                        print(e)

                # search edge
                matches = re.findall("^y\$(.*)\$(.*)\$(.*)\$([^ \t]+) +([^ \t]+)", line)
                if (len(matches) > 0):
                    node_1, node_2, snode_1, snode_2, value = matches[0]
                    snode_1, service_id, sla_id = snode_1.split("_")
                    snode_2, service_id, sla_id = snode_2.split("_")

                    node_1 = session.query(Node).filter(Node.name == node_1).one()
                    node_2 = session.query(Node).filter(Node.name == node_2).one()

                    edge = session.query(Edge).filter(or_(and_(Edge.node_1 == node_1, Edge.node_2 == node_2),
                                                          and_(Edge.node_1 == node_2, Edge.node_2 == node_1))).one()
                    snode_1 = session.query(ServiceNode).filter(
                        and_(ServiceNode.sla_id == sla_id, ServiceNode.service_id == service_id,
                             ServiceNode.name == snode_1)).one()
                    snode_2 = session.query(ServiceNode).filter(
                        and_(ServiceNode.sla_id == sla_id, ServiceNode.service_id == service_id,
                             ServiceNode.name == snode_2)).one()
                    sedge_id = session.query(ServiceEdge.id).filter(
                        and_(ServiceEdge.node_1_id == snode_1.id, ServiceEdge.node_2_id == snode_2.id,
                             ServiceEdge.service_id == service_id, ServiceEdge.sla_id == sla_id)).one()[0]

                    edgeMapping = EdgeMapping(edge_id=edge.id, serviceEdge_id=sedge_id)
                    edgesSol.append(edgeMapping)

                matches = re.findall("^objective value: *([0-9\.]*)$", line)
                if (len(matches) > 0):
                    objective_function = float(matches[0])
                    continue

                matches = re.findall("^(.*)_master", line)
                if (len(matches) > 0):
                    violations.append(matches[0])
                    continue

            mapping = Mapping(node_mappings=nodesSols, edge_mappings=edgesSol, objective_function=objective_function)
            return mapping


    @classmethod
    def cleanup(cls):
        for f in [os.path.join(RESULTS_FOLDER, "service.edges.data"),
                  os.path.join(RESULTS_FOLDER, "service.path.data"),
                  os.path.join(RESULTS_FOLDER, "service.path.delay.data"),
                  os.path.join(RESULTS_FOLDER, "service.nodes.data"),
                  os.path.join(RESULTS_FOLDER, "CDN.nodes.data"),
                  os.path.join(RESULTS_FOLDER, "starters.nodes.data"),
                  os.path.join(RESULTS_FOLDER, "cdnmax.data"),
                  os.path.join(RESULTS_FOLDER, "VHG.nodes.data"),
                  os.path.join(RESULTS_FOLDER, "VCDN.nodes.data")]:
            if os.path.isfile(f):
                os.remove(f)

    def write_service_topology(self, topo, path="."):

        if not os.path.exists(os.path.join(RESULTS_FOLDER, path)):
            os.makedirs(os.path.join(RESULTS_FOLDER, path))

        id = "default"
        mode = "w"
        # slas = self.slas
        slas = [self.sla]

        # write info on the edge
        with open(os.path.join(RESULTS_FOLDER, path, "service.edges.data"), mode) as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)
                for start, end, bw in topo.dump_edges():
                    f.write("%s\t\t%s_%s\t\t%lf\n" % (("%s_%s" % (start, postfix)).ljust(20), end, postfix, bw))

        with open(os.path.join(RESULTS_FOLDER, path, "service.nodes.data"), mode) as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)

                for snode_id, cpu, bw in topo.getServiceNodes():
                    f.write("%s\t\t%lf\t\t%lf\n" % (("%s_%s" % (snode_id, postfix)).ljust(20), cpu, bw))
                    # sys.stdout.write("%s_%s %lf\n" % (snode_id, postfix, cpu))


                    # write constraints on CDN placement
        with open(os.path.join(RESULTS_FOLDER, path, "CDN.nodes.data"), mode) as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)
                self.merged_sla.get_cdn_nodes()
                for node, mapping, bw in topo.get_CDN():
                    f.write("%s_%s %s\n" % (node, postfix, mapping))

        # write constraints on starter placement
        with open(os.path.join(RESULTS_FOLDER, path, "starters.nodes.data"), mode) as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)
                for s, topo, bw in topo.get_Starters():
                    f.write("%s_%s %s %lf\n" % (s, postfix, topo, bw))

        # write the names of the VHG Nodes
        with open(os.path.join(RESULTS_FOLDER, path, "VHG.nodes.data"), mode) as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)
                for vhg in topo.get_vhg():
                    f.write("%s_%s\n" % (vhg, postfix))

        # write the names of the VCDN nodes
        with open(os.path.join(RESULTS_FOLDER, path, "VCDN.nodes.data"), mode) as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)
                for vcdn in topo.get_vcdn():
                    f.write("%s_%s\n" % (vcdn, postfix))

                    # write path to associate e2e delay

        with open(os.path.join(RESULTS_FOLDER, path, "service.path.delay.data"), "w") as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)

                for apath in topo.dump_delay_paths():
                    f.write("%s_%s %lf\n" % (apath, postfix, topo.delay))

        # write e2e delay constraint
        with open(os.path.join(RESULTS_FOLDER, path, "service.path.data"), "w") as f:
            for sla in slas:
                postfix = "%d_%d" % (id, sla.id)

                for apath, s1, s2 in topo.dump_delay_routes():
                    f.write("%s_%s %s_%s %s_%s\n" % (apath, postfix, s1, postfix, s2, postfix))

    def solve(self, service, substrate, path, use_heuristic=True, reopt=False):
        session = Session()
        service.write(path)
        substrate.write(path)
        session.flush()
        mapping = self.__solve_inplace(path=path, use_heuristic=use_heuristic, reopt=reopt)

        service.mapping = mapping
        if mapping is not None:
            mapping.substrate = substrate
            session.add(mapping)
        session.flush()
