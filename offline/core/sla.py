import scipy
import scipy.integrate as integrate

tcp_win = 65535.0


def concurrentUsers(t, m, sigma, duration):
    return integrate.quad(
        lambda x: 1 / (sigma * scipy.sqrt(2 * scipy.pi) * scipy.exp(-(x - m) ** 2.0 / (2 * sigma ** 2))), t - duration,
        t)[0]


class Sla:
    def __init__(self, bitrate, count, time_span, movie_duration, start, cdn,max_cdn_to_use=2):
        self.start = start
        self.cdn = cdn
        self.delay = tcp_win / bitrate * 1000.0
        self.bandwidth = count * bitrate * movie_duration / time_span
        self.max_cdn_to_use=max_cdn_to_use


    def __str__(self):
        return "%d %d %lf %lf" % (self.start, self.cdn, self.delay, self.bandwidth)

        # Throughput = TCPWindow / round-trip-delay


def write_sla(sla, seed=None):
    with open("CDN.nodes.data", 'w') as f:
        f.write("%s \n" % sla.cdn)

    with open("starters.nodes.data", 'w') as f:
        f.write("%s \n" % sla.start)


def getRandomBitrate(rs):
    n = rs.uniform(0,100)
    if n < 25: #LD
        return 666666
    elif n < 75:
        return 1555555# SD
    else:
        return 5000000 #HD








def generate_random_slas(rs, substrate, count=1000,start_count=None,end_count=2,max_cdn_to_use=2):
    res = []
    for i in range(0, count):


        bitrate = getRandomBitrate(rs)

        #bitrate = rs.choice([   400000, 500000, 600000])

        concurent_users = max(rs.normal(20000, 5000), 1000)


        #concurent_users = max(rs.normal(20000, 5000), 5000)
        time_span = max(rs.normal(24 * 60 * 60, 60 * 60), 0)
        movie_duration = max(rs.normal(60 * 60, 10 * 60), 0)

        if start_count is None:
            start_count_drawn=rs.choice([1,2,3,4])
        else:
            start_count_drawn=start_count

        draws = rs.choice(substrate.nodesdict.keys(), size=start_count_drawn+end_count, replace=False).tolist()

        start=[]
        cdn=[]
        for i in range(1,start_count_drawn+1):
            start.append(draws.pop())
        for i in range(1,end_count+1):
            cdn.append(draws.pop())


        res.append(Sla(bitrate, concurent_users, time_span, movie_duration, start, cdn,max_cdn_to_use=max_cdn_to_use))

    return res
