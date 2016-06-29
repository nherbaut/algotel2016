FROM debian
MAINTAINER David Bainbridge <dbainbri@ciena.com>

ENV DEBIAN_FRONTEND noninteractive

ENV MININET_REPO git://github.com/mininet/mininet
ENV MININET_INSTALLER ./mininet/util/install.sh
ENV INSTALLER_SWITCHES -fbinptvwyx

ENV CONTAINERNET_REPO git://github.com/mpeuster/containernet.git
ENV CONTAINERNET_INSTALLER ./containernet/util/install.sh

WORKDIR /tmp

# Update and install minimal.
RUN \
    apt-get update \
        --quiet \
    && apt-get install \
        --yes \
        --no-install-recommends \
        --no-install-suggests \
    autoconf \
    automake \
    ca-certificates \
    git \
    curl \
    libtool \
    net-tools \
    openssh-client \
    patch \
    vim \
    nano \
    apt-transport-https \
    ca-certificates \
    curl \
    iptables\
    sudo \
    python-pip \
    lxc \
    build-essential \
    libgmp3-dev \
    libreadline6 \
    libreadline6-dev \
    python-pip \
    graphviz \
    python-matplotlib \
    python-scipy \
    python-numpy \
    pkg-config \
    python \
    zlib1g-dev \
    libncurses5-dev \
    bison \
    flex \
    python2.7 \
    python2.7-dev \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \

#RUN easy_install python-pip
    && pip install  \
        setuptools \
        urllib3 \
        pytest \
        docker-py==1.7.1 \
        cycler==0.10.0 \
        decorator==4.0.9 \
        haversine==0.4.5 \
        networkx==1.11 \
        pygraphml==2.0 \
        pyparsing==2.1.1 \
        python-dateutil==2.5.3 \
        pytz==2016.4 \
        six==1.10.0 \


#install docker
 
    && curl -sSL https://get.docker.com/ | sh \
# Clone and install.
    && git clone  $CONTAINERNET_REPO \

# A few changes to make the install script behave.
    #&& sed -e 's/sudo //g' \
    #	-e 's/~\//\//g' \
    #	-e 's/\(apt-get -y -q install\)/\1 --no-install-recommends --no-install-suggests/g' \
    #	-i $CONTAINERNET_INSTALLER \


# Install script expects to find this. Easier than patching that part of the script.
    && touch /.bashrc \

# Proceed with the install.
    && chmod +x $CONTAINERNET_INSTALLER \
    && ./$CONTAINERNET_INSTALLER -nfv \

# Clean up source.
    && rm -rf /tmp/mininet \
              /tmp/openflow \

# Clean up packages.
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


 

# Create a start script to start OpenVSwitch
RUN echo 'DOCKER_OPTS="--insecure-registry 172.17.0.1:5000"' >/etc/default/docker
COPY docker-entry-point /docker-entry-point
RUN chmod 755 /docker-entry-point
VOLUME ["/data"]
WORKDIR /data
COPY ./ ./

# Default command.
ENTRYPOINT ["/docker-entry-point"]
