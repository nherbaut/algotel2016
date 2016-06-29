#!/usr/bin/env python

from haversine import haversine
from pygraphml import GraphMLParser
import os
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../results')
DATA_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data')


class bcolors:


    @staticmethod
    def color_out(value):
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
        if value > 80:
            return OKGREEN + str(value) + ENDC
        elif value > 60:
            return OKBLUE + str(value) + ENDC
        elif value > 40:
            return WARNING + str(value) + ENDC
        elif value > 20:
            return FAIL +str(value) + ENDC
        else:
            return FAIL+BOLD+str(value)+ENDC


class Substrate:
    def __str__(self):
        #print [x[1] for x in self.nodesdict.items()]
        return "%e\t%e" % (self.get_edges_sum(),self.get_edges_sum())

    def get_edges_sum(self):
        return sum([x[2] for x in self.edges])


    def get_nodes_sum(self):
        return sum([x[1] for x in self.nodesdict.items()])

    def __init__(self, edges, nodesdict,cpuCost=2000,netCost=20000.0/10**9):
        self.edges = edges
        self.nodesdict = nodesdict
        self.edges_init = sorted(edges, key=lambda x: "%s%s" % (str(x[0]), str(x[1])))
        self.nodesdict_init = nodesdict.copy()
        self.cpuCost=cpuCost
        self.netCost=netCost

    def write(self, edges_file=os.path.join(RESULTS_FOLDER,"substrate.edges.data"), nodes_file=os.path.join(RESULTS_FOLDER,"substrate.nodes.data")):
        edges = self.edges
        nodesdict = self.nodesdict
        with open(edges_file, 'w') as f:
            for l in sorted(edges, key=lambda x: "%s%s" % (str(x[0]), str(x[1]))):
                f.write("%s\t%s\t%e\t%e\n" % (l[0], l[1], float(l[2]), l[3]))

        with open(nodes_file, 'w') as f:
            for nodekey in sorted(nodesdict.keys()):
                node = nodesdict[nodekey]
                f.write("%s\t%lf\n" % (nodekey, node))

        with open(edges_file+"_pc", 'w') as f:
            for idx, val in enumerate(sorted(edges, key=lambda x: "%s%s" % (str(x[0]), str(x[1])))):
                f.write("%s\t%s\t%s\t%s\n" % (val[0], val[1], bcolors.color_out(float(val[2])/float(self.edges_init[idx][2])*100), bcolors.color_out(float(val[3])/float(self.edges_init[idx][3])*100)))

        with open(nodes_file+"_pc", 'w') as f:
            for nodekey in sorted(nodesdict.keys()):
                node = bcolors.color_out(float(nodesdict[nodekey])/float(self.nodesdict_init[nodekey])*100)
                f.write("%s\t%s\n" % (nodekey, node))

        with open(os.path.join(RESULTS_FOLDER,"cpu.cost.data"),"w") as f:
            f.write("%lf\n"%self.cpuCost)

        with open(os.path.join(RESULTS_FOLDER,"net.cost.data"),"w") as f:
            f.write("%lf\n"%self.netCost)


    @classmethod
    def fromSpec(cls,width,height,bw,delay,cpu):
        edges = []
        nodesdict = {}

        for i in range(1,width+1):
            for j in range(1,height+1):
                nodesdict[str("%02d%02d"%(i,j))] = cpu

        for i in range(1,width+1):
            for j in range(1,height+1):
                if j+1 <= height:
                    edges.append(("%02d%02d"%(i,j), "%02d%02d"%(i,j+1), bw, delay))
                if i+1 <= width:
                    edges.append(("%02d%02d"%(i,j), "%02d%02d"%(i+1,j), bw, delay))
                if j+1 <= height and i+1 <= width:
                    edges.append(("%02d%02d"%(i,j), "%02d%02d"%(i+1,j+1), bw, delay))


        return cls(edges, nodesdict)

    @classmethod
    def fromSpecTree(cls,width,height,bw,delay,cpu):
        edges = []
        nodesdict = {}

        for i in range(1,width+1):
            for j in range(1,height+1):
                nodesdict[str("%02d%02d"%(i,j))] = cpu

        for i in range(1,width+1):
            for j in range(1,height+1):
                if j+1 <= height:
                    edges.append(("%02d%02d"%(i,j), "%02d%02d"%(i,j+1), bw, delay))
                if i+1 <= width:
                    edges.append(("%02d%02d"%(i,j), "%02d%02d"%(i+1,j), bw, delay))
                if j+1 <= height and i+1 <= width:
                    edges.append(("%02d%02d"%(i,j), "%02d%02d"%(i+1,j+1), bw, delay))


        return cls(edges, nodesdict)




    @classmethod
    def fromFile(cls, edges_file=os.path.join(RESULTS_FOLDER,"substrate.edges.data"), nodes_file=os.path.join(RESULTS_FOLDER,"substrate.nodes.data")):

        edges = []
        nodesdict = {}

        with open(edges_file, 'r') as f:
            for line in f.read().split("\n"):
                if len(line) > 2:
                    node1, node2, bw, delay = line.split("\t")
                    edges.append((node1, node2, float(bw), float(delay)))

        with open(nodes_file, 'r') as f:
            for line in f.read().split("\n"):
                if len(line) > 2:
                    nodeid, cpu = line.split("\t")
                    nodesdict[nodeid] = float(cpu)

        return cls(edges, nodesdict)


    @classmethod
    def fromGraph(cls,rs,file):
        parser = GraphMLParser()

        g = parser.parse(file)

        nodes = {str(n.id): n for n in g.nodes()}
        edges = [(str(e.node1.id), str(e.node2.id), float(e.attributes()["d42"].value),
                  get_delay(nodes[str(e.node1.id)], nodes[str(e.node2.id)]))
                 for e in g.edges() if "d42" in e.attributes() and isOK(nodes[str(e.node1.id)], nodes[str(e.node2.id)])]

        # for which we have all the data
        valid_nodes = list(set([e[0] for e in edges] + [e[1] for e in edges]))

        nodes = set([str(n.id) for n in g.nodes() if str(n.id) in valid_nodes])
        nodesdict = {}

        for l in nodes:
            value = max(rs.normal(100, 5, 1)[0], 0)
            nodesdict[str(l)] = value

        return cls(edges, nodesdict)

    def consume_service(self, service, mapping):
        try:
            #print "consuming..."
            for ns in mapping.nodesSol:
                self.nodesdict[ns[0]] = self.nodesdict[ns[0]] - service.nodes[ns[1]].cpu
                #print "\teater %lf from %s, remaining %s" % (service.nodes[ns[1]].cpu, ns[1], self)
            for es in mapping.edgesSol:
                if not deduce_bw(es, self.edges, service):
                    backward = (es[1], es[0], es[2], es[3])
                    deduce_bw(backward, self.edges, service)
        except ValueError as e:
            print e
        return


def deduce_bw(es, edges, service):
    candidate_edges = filter(lambda x: x[0] == es[0] and x[1] == es[1], edges)
    if len(candidate_edges) != 0:
        sub_edge = candidate_edges[0]
        service_edge = service.edges["%s %s" % (es[2], es[3])]
        edges.remove(sub_edge)
        edges.append((sub_edge[0], sub_edge[1], sub_edge[2] - service_edge.bw, sub_edge[3]))
        if sub_edge[2] - service_edge.bw <0:
            print "hein?"
        return True
    return False


def get_delay(node1, node2):
    return haversine((float(node1.attributes()["d29"].value), float(node1.attributes()["d32"].value)),
                     (float(node2.attributes()["d29"].value), float(node2.attributes()["d32"].value))) / (299.300 * 0.6)


def isOK(node1, node2):
    try:
        get_delay(node1, node2)
    except:
        return False
    return True


def get_substrate(rs, file=os.path.join(DATA_FOLDER,'Geant2012.graphml')):

    su=Substrate.fromGraph(rs,file)
    su.write()

    return su
