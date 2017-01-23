from offline.discrete.utils import *


class User(object):
    def __init__(self, graph, servers, env, location, start_time, content_drawer):
        self.g = graph
        self.servers = servers
        self.env = env

        self.location = location
        self.action = env.process(self.run())
        self.start_time = start_time
        self.content_drawer = content_drawer

        def consume_content(content, bw, cap):
            # logging.debug("[%s]\t%s \t consume content %s" % (self.env.now, self.location, str(content)))
            winner, price = create_content_delivery(self.env, graph, servers, content, location, bw, cap)
            Monitoring.push_average("price", env.now, price)
            # logging.info(green("consumming %s from %s" % (content, location)))
            return winner

        self.consume_content = consume_content

        def release_content(winner, bw, cap):
            release_content_delivery(self.env, graph, location, winner, bw, cap)
            # logging.info(yellow("releasing session from %s" % (location)))

        self.release_content = release_content

    def run(self):
        yield self.env.timeout(self.start_time)

        try:
            content, bw, cap, duration = self.content_drawer()
            Monitoring.push("REQUEST", self.env.now, 1)
            Monitoring.push("USER", self.env.now, 1)
            winner = self.consume_content(content, bw, cap)
            yield self.env.timeout(duration)
            self.release_content(winner, bw, cap)
        except NoPeerAvailableException as e:
            # logging.info(rd("failed to fetch content %s from %s ") % (self.content, self.location))
            pass
        Monitoring.push("USER", self.env.now, -1)
