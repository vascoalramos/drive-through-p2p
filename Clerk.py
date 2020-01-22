# coding: utf-8

import pickle
import socket
import random
import logging
import configparser
import threading
import uuid
from RingNode import RingNode
from utils import work

# configure the log with INFO level
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

# get configuration file values with work times for each equipment
config = configparser.ConfigParser()
config.read("conf.ini")


class Clerk(threading.Thread):
    def __init__(self, nOfEntity=0, port=5001, id=1, name="CLERK", timeout=3, TG=0, ring=5000, ringSize=4):
        threading.Thread.__init__(self)

        if nOfEntity == 0:
            loggerName = name
        else:
            loggerName = name+"-"+str(nOfEntity)
        self.logger = logging.getLogger(loggerName)

        # Creating special socket for receiving clients' requests
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(timeout)
        self.client_socket.bind(('localhost', port-50))

        self.comm_clerk = RingNode(loggerName, id, ('localhost', port), name,
                                   timeout, TG, ('localhost', ring), ringSize)  # communication thread

        self.port = port
        self.timeout = timeout
        self.count = 0

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
        self.logger.info("CREATING CLERK")
        self.comm_clerk.start()
        self.logger.debug("CREATED CLERK SUCCESSFULLY")
        self.logger.debug("#Threads: %s", threading.active_count())
        self.clk_work(self.comm_clerk, self.port, self.timeout)

    def clk_work(self, comm, port, timeout):

        # get discovery table
        self.discovery_table = comm.get_ringIDs()
        while self.discovery_table == None:
            self.discovery_table = comm.get_ringIDs()
            work(0.5)
        self.logger.info("Discovery Table from Comm thread: %s",
                         self.discovery_table)

        while True:
            request = comm.get_in_queue()
            if request is not None:
                self.logger.info("Request from queue: %s", request)

                # Wait for a random time
                delta = random.gauss(int(config['ACTION']['MEAN']), float(
                    config['ACTION']['STD_DEVIATION']))
                self.logger.info('Wait for %f seconds', delta)
                work(delta)

                client_addr = request['args']['CLIENT_ADDR']
                order_id = uuid.uuid1()
                msg = {'method': 'ORDER_RECEIVED', 'args': order_id}
                self.send(client_addr, msg)  # send ticket to client
                if isinstance(self.discovery_table['CHEF'], list):
                    msg = {'method': 'TOKEN', 'args': {'method': 'COOK', 'args': {
                        'id': self.discovery_table['CHEF'][self.count], 'order': request['args']['order'],
                        'CLIENT_ADDR': request['args']['CLIENT_ADDR'], 'TICKET': order_id}}}
                    self.count = (
                        self.count+1) % len(self.discovery_table['CHEF'])
                else:
                    msg = {'method': 'TOKEN', 'args': {'method': 'COOK', 'args': {
                        'id': self.discovery_table['CHEF'], 'order': request['args']['order'],
                        'CLIENT_ADDR': request['args']['CLIENT_ADDR'], 'TICKET': order_id}}}
                self.logger.debug(msg)
                comm.put_out_queue(msg)
