# coding: utf-8

import time
import pickle
import socket
import random
import logging
import argparse
import configparser
import threading
from utils import contains_successor
from queue import Queue


class RingNode (threading.Thread):
    def __init__(self, loggerName, ID, port, name, timeout, TG, ring, ringSize, EG=0, blackList=["GRILL_TOKEN", "FRIER_TOKEN", "DRINKS_TOKEN"]):
        # TG - Token generator - The Entity that creates and starts the token passing
        # EG - Equipment generator - The Entity that creates and starts the Equipment passing
        # blackList - Types of message the entity should ignore and just pass forward
        # ring - Flag to check if entity is inside the ring or not

        threading.Thread.__init__(self)
        self.id = ID
        self.port = port
        self.ring = ring
        self.name = name
        self.size = ringSize
        self.ringIDs = {}
        self.TG = TG  # Token Generator - Responsible for token creation
        self.inQueue = Queue()
        self.outQueue = Queue()

        self.blackList = blackList
        self.EG = EG

        if ring is None:
            self.succ_ID = self.id
            self.succ_port = self.port
            self.inside_Token_Ring = True

        else:
            self.succ_ID = None
            self.succ_port = None
            self.inside_Token_Ring = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)
        self.logger = logging.getLogger(loggerName)

    def recv(self):
        try:
            p, addr = self.socket.recvfrom(1024)
        except socket.timeout:
            return None, None
        else:
            if len(p) == 0:
                return None, addr
            else:
                return p, addr

    def getSelfID(self):
        return self.id

    def send(self, address, o):
        p = pickle.dumps(o)
        self.socket.sendto(p, address)

    def get_in_queue(self):
        if self.inQueue.empty():
            return None
        return self.inQueue.get()

    def get_out_queue(self):
        if self.outQueue.empty():
            return None
        return self.outQueue.get()

    def put_in_queue(self, o):
        self.inQueue.put(o)

    def put_out_queue(self, o):
        self.outQueue.put(o)

    def get_ringIDs(self):

        count = 0
        for i in self.ringIDs:
            if type(self.ringIDs[i]) is list:
                count += len(self.ringIDs[i])
            else:
                count += 1

        if count != self.size:
            return None
        return self.ringIDs

    def entity_join(self, args):
        self.logger.debug('Entity join: %s', args)
        port = args['port']
        identification = args['id']

        if self.id == self.succ_ID:
            self.succ_ID = identification
            self.succ_port = port
            args = {'succ_ID': self.id, 'succ_PORT': self.port}
            self.send(port, {'method': 'NODE_JOIN_REP', 'args': args})

        elif contains_successor(self.id, self.succ_ID, identification):
            args = {'succ_ID': self.succ_ID, 'succ_PORT': self.succ_port, }
            self.succ_ID = identification
            self.succ_port = port
            self.send(port, {'method': 'NODE_JOIN_REP', 'args': args})
        else:
            self.logger.debug('Find Successor(%d)', args['id'])
            self.send(self.succ_port, {
                      'method': 'NODE_JOIN_REQ', 'args': args})

    ##############################################NODE DISCOVERY##############################################
    # Method:
        # 1. First node starts sending NODE_DISCOVERY packages with the args containg a dictionary of KEY: ID ; VALUE: Type
        # {type:NODE_DISCOVERY,args{ {ENTITY-IDdictionary}, int rounds }}

        # 2. Package gets sent to the next node in ring
        # 3. When it reaches a node, the node checks whether the dictionary is complete:
        # NOT COMPLETE - Add our ENTITY-ID to the dictionary
        # COMPLETE - #1. Increment rounds
        # 2. Check if rounds is 1 or 2
        # 2: [STOP PROCESS]
        # 1: Register the dictionary as our own

        # 4. Send package to next node

        # Q - How to check if it's full?
        # A - Check if the current node's ID is the same as the Token Generator's ID (since this is the one where the discovery
        # starts)

        # Q - How many go-rounds does this method take?
        # A - 2. 1 to build the dictionary + 1 to register on each node

        # Q - How to check if we're done?
        # A - We use a regDone int that's used to check how many nodes have registered the dictionary

    def nodeDiscovery(self, pickleObj=None):

        if pickleObj == None and self.id == self.TG:  # First time we send a discovery message
            msg = {'method': 'NODE_DISCOVERY', 'args': {
                "idDictionary": {self.name: self.id}, "rounds": 0}}
            return msg

        message = pickleObj
        ringIDs = message["args"]["idDictionary"]
        rounds = message["args"]["rounds"]

        if not self.name in ringIDs:  # If we don't already have an entity with this name, add it to our ringIDs
            ringIDs[self.name] = self.id

        # If we don't already have the current id registered to the entity name in our ringIDS and it's not a list yet, make the value a list
        elif not type(ringIDs[self.name]) is list and not ringIDs[self.name] == self.id:
            ringIDs[self.name] = [ringIDs[self.name], self.id]

        # Check if its a list already and if we already have this id in the list
        elif type(ringIDs[self.name]) is list and not self.id in ringIDs[self.name]:
            ringIDs[self.name].append(self.id)

        else:  # Else, it means we already have this specific node registered :)
            # The dictionary's complete because there are no repeat ID's so we check if we're at node 0 (and increase rounds if necessary)
            if self.id == self.TG:
                if rounds == 0:
                    rounds += 1
                else:
                    return None  # Means the process is over

            self.ringIDs = ringIDs
            self.logger.info(
                'REGISTERING IDs AT NODE ID: %.1f - %s', self.id, self.ringIDs)

        msg = {'method': 'NODE_DISCOVERY', 'args': {
            "idDictionary": ringIDs, "rounds": rounds}}

        return msg

    ##############################################NODE DISCOVERY##############################################

    def run(self):
        self.socket.bind(self.port)

        while not self.inside_Token_Ring:
            o = {'method': 'NODE_JOIN_REQ', 'args': {
                'port': self.port, 'id': self.id}}
            self.send(self.ring, o)
            p, port = self.recv()
            if p is not None:
                o = pickle.loads(p)
                self.logger.debug('O: %s', o)
                if o['method'] == 'NODE_JOIN_REP':
                    args = o['args']
                    self.succ_ID = args['succ_ID']
                    self.succ_port = args['succ_PORT']
                    self.inside_Token_Ring = True

        discoveryStarted = False  # Flag to check if the discovery process has started
        if self.id == self.TG:
            o = {'method': 'TOKEN', 'args': {'method': 'count', 'args': 0}}
            self.send(self.succ_port, o)

        if self.id == self.EG:  # Create and start sending the equipment tokens through the ring
            self.logger.debug("Equipments Circulating")
            o = {'method': 'GRILL_TOKEN', 'args': {'available': 1}}
            self.logger.info("CREATING TOKEN GRILL")
            self.send(self.succ_port, o)
            o = {'method': 'FRIER_TOKEN', 'args': {'available': 1}}
            self.logger.info("CREATING TOKEN FRYER")
            self.send(self.succ_port, o)
            o = {'method': 'DRINKS_TOKEN', 'args': {'available': 1}}
            self.logger.info("CREATING TOKEN DRINKS")
            self.send(self.succ_port, o)

        while True:
            p, port = self.recv()
            if p is not None:
                o = pickle.loads(p)

                # If the message type is in the blacklist, pass it forward and ignore it
                if o['method'] in self.blackList:
                    self.send(self.succ_port, o)

                elif o['method'] == 'NODE_JOIN_REQ':
                    self.entity_join(o['args'])

                elif o['method'] == 'GRILL_TOKEN' or o['method'] == 'DRINKS_TOKEN' or o['method'] == 'FRIER_TOKEN':
                    # If the equipment is in use, keep the token rolling
                    if o['args']['available'] == 0:
                        if self.outQueue.empty():
                            self.send(self.succ_port, o)
                        else:
                            o = self.outQueue.get()
                            self.send(self.succ_port, o)
                            self.logger.debug("Message to send: %s", o)

                    # Else give it to the entity
                    else:
                        self.inQueue.put(o)
                        if self.outQueue.empty():
                            message = {
                                'method': o['method'], 'args': {'available': 0}}
                        else:
                            message = self.outQueue.get()
                        self.send(self.succ_port, message)

                elif o['method'] == 'TOKEN':
                    # If the token contains the COUNT method (used to check if the ring is complete)
                    if o['args']['method'] == 'count':
                        count = o['args']['args']
                        if self.id != self.TG:
                            count += 1
                            msg = {'method': 'TOKEN', 'args': {
                                'method': 'count', 'args': count}}
                            self.send(self.succ_port, msg)
                        else:
                            # IF count = 3 it means that the ring is complete so we'll start the discovery process
                            if count == self.size-1 and discoveryStarted == False:
                                self.logger.info("Starting Discovery Process")
                                discoveryStarted = True
                                message = self.nodeDiscovery()
                                self.send(self.succ_port, message)
                            else:
                                count = 0
                                msg = {'method': 'TOKEN', 'args': {
                                    'method': 'count', 'args': count}}
                                self.send(self.succ_port, msg)

                    # If the token is empty
                    elif o['args']['method'] == None:
                        if self.outQueue.empty():
                            self.send(self.succ_port, o)
                        else:
                            o = self.outQueue.get()
                            self.send(self.succ_port, o)
                            self.logger.debug("Message to send: %s", o)

                    else:
                        if o['args']['args']['id'] == self.id:
                            self.logger.debug(o)
                            self.inQueue.put(o['args'])
                            if self.outQueue.empty():
                                message = {'method': 'TOKEN', 'args': {
                                    'method': None, 'args': None}}
                            else:
                                message = self.outQueue.get()
                            self.send(self.succ_port, message)

                        else:
                            self.send(self.succ_port, o)
                            self.logger.debug("Message to send: %s", o)

                elif o["method"] == "NODE_DISCOVERY":
                    self.logger.info(
                        'Discovery Process reached Node:  ID: %.1f', self.id)

                    message = self.nodeDiscovery(o)

                    if message is None:
                        self.logger.info("ENDED DISCOVERY PROCESS")
                        message = {'method': 'TOKEN', 'args': {
                            'method': None, 'args': None}}

                    # If args = 1 it means that we're already on the 2nd go-around so we can stop the discovery process for that entity
                    elif message["args"]["rounds"] == 1:
                        self.logger.debug(
                            'My Successor: %s ', self.succ_ID)
                        self.logger.info(
                            "Ending Discovery Process for ID %.1f", self.id)

                    self.logger.debug(message)
                    self.send(self.succ_port, message)

        self.logger.info("Closing")
