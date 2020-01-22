# coding: utf-8

import time
import pickle
import socket
import random
import logging
import configparser
import threading
from RingNode import RingNode
from utils import work
from queue import Queue

# configure the log with INFO level
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

# get configuration file values with work times for each equipment
config = configparser.ConfigParser()
config.read("conf.ini")


class Restaurant(threading.Thread):
    def __init__(self, nOfEntity=0, port=5000, id=0, name="RESTAURANT", timeout=3, TG=0, ring=None, ringSize=4, EG=0, blackList=[]):
        threading.Thread.__init__(self)  # worker thread

        if nOfEntity == 0:
            loggerName = name
        else:
            loggerName = name+"-"+str(nOfEntity)
        self.logger = logging.getLogger(loggerName)

        # Creating special socket for receiving clients' requests
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(timeout)
        self.client_socket.bind(('localhost', port-50))

        self.comm_restaurant = RingNode(loggerName, id, ('localhost', port), name,
                                        timeout, TG, ring, ringSize, EG, blackList)  # communication thread

        self.port = port
        self.timeout = timeout

    def recv(self):
        try:
            p, addr = self.client_socket.recvfrom(1024)
        except socket.timeout:
            return None, None
        else:
            if len(p) == 0:
                return None, addr
            else:
                return p, addr

    def send(self, address, o):
        p = pickle.dumps(o)
        self.client_socket.sendto(p, address)

    def run(self):
        self.logger.info("CREATING RESTAURANT")
        self.comm_restaurant.start()
        self.logger.debug("CREATED RESTAURANT SUCCESSFULLY")
        self.logger.debug("#Threads: %s", threading.active_count())
        self.rest_work(self.comm_restaurant, self.port, self.timeout)

    def rest_work(self, comm, port, timeout):
        # get discovery table
        self.discovery_table = comm.get_ringIDs()
        while self.discovery_table == None:
            self.discovery_table = comm.get_ringIDs()
            work(0.5)
        self.logger.info("Discovery Table from Comm thread: %s",
                         self.discovery_table)

        done = False
        while not done:
            p, addr = self.recv()

            if p is not None:
                o = pickle.loads(p)
                self.logger.info("Request received: %s", o)

                if o['method'] == 'ORDER':
                    msg = {'method': 'TOKEN', 'args': {'method': 'CLIENT_ORDER', 'args': {
                        'id': self.discovery_table['CLERK'], 'order': o['args'], 'CLIENT_ADDR': addr}}}
                    comm.put_out_queue(msg)

                elif o['method'] == 'PICKUP':
                    msg = {'method': 'TOKEN', 'args': {'method': 'CLIENT_PICKUP', 'args': {
                        'id': self.discovery_table['WAITER'], 'CLIENT_ADDR': addr, 'TICKET': o['args']}}}
                    comm.put_out_queue(msg)

            else:
                request = comm.get_in_queue()
                if request is not None:
                    if request['method'] == 'GRILL_TOKEN':
                        self.logger.debug("GRILL KEEPALIVE")
                        comm.put_out_queue(request)

                    elif request['method'] == 'FRIER_TOKEN':
                        self.logger.debug("FRIER KEEPALIVE")
                        comm.put_out_queue(request)

                    elif request['method'] == 'DRINKS_TOKEN':
                        self.logger.debug("DRINKS KEEPALIVE")
                        comm.put_out_queue(request)
