# Std-library modules
import socket
import sys

import select
import json
import time
import random
from typing import List, Optional

# Custom modules
from client_msg_handler import handle_client_msg
from election_msg_handler import handle_req_vote_msg, handle_incoming_vote_msg
from append_entries_msg_handler import handle_append_entries_msg
from raft_data_structs import LogEntry

MAX_UDP_PACKET_SIZE = 65535
BROADCAST = "FFFF"


class Replica:
    def __init__(self, port, id, others):
        self.port: int = port
        self.id: str = id
        self.others: [] = others
        # Create an IPv4, UDP socket
        self.socket: socket.socket = socket.socket(socket.AF_INET,
                                                   socket.SOCK_DGRAM)
        # Bind the socket to local host, so all network interfaces on the
        # machine can access the socket
        # Uses port 0 to specify the first available port from the OS
        self.socket.bind(('localhost', 0))

        # Create a heartbeat timer in a random interval 150-300 MS
        self.timer_start: float = time.time()
        # Wait time in milliseconds before our heartbeat timer expires
        self.wait_time: float = random.randint(150, 300) / 1000.0

        # Voting data - initialized to default values
        self.curr_state: str = 'follower'  # All replicas start off as
        # followers
        self.candidate_voted_for: Optional[str] = None
        # The highest term this replica has encountered so far
        self.curr_term: int = 0
        self.leader: str = 'FFFF'  # Initially, the leader is unknown
        # Use a set of replicas who voted for us to represent votes received
        # this term
        self.voters_this_term: set = set()

        # Leader State data - initialized to default values
        # The key-value map that actually holds our data
        self.datastore: dict = {}
        # The log of this replica : LogEntry[], each LogEntry encapsulates a
        # message and term.
        self.entry_log: List[LogEntry] = []

        # Broadcast a 'hello' message to all other replicas on our LAN to
        # indicate this replica is up
        hello_msg: dict = {
            "src": self.id, "dst": BROADCAST, "leader": BROADCAST,
            "type": "hello"
        }
        self.log(f"Replica {self.id} starting up")
        self.send(hello_msg)

    def send(self, msg):
        """
        Sends and encodes the given JSON message to this replica's 'LAN'
        """
        self.socket.sendto(
            json.dumps(msg).encode('utf-8'),
            ('localhost', self.port)
        )
        print(f'Sent msg: {msg}')

    def log(self, msg):
        sys.stderr.write(f'{msg}\n')
        sys.stderr.flush()

    def run(self):
        self.log('Run!')
        while True:
            # Wait for messages from our LAN on our socket
            readable_socks: List[socket.socket] = select.select([self.socket],
                                                                [], [])[0]
            for ready_sock in readable_socks:
                encoded_msg: bytes = ready_sock.recvfrom(MAX_UDP_PACKET_SIZE)[0]
                msg: dict = json.loads(encoded_msg.decode('utf-8'))
                self.handle_msg(msg)
            if self.curr_state in ('candidate', 'follower'):
                self.check_heartbeat_timeout()
            elif self.curr_state == 'leader':
                self.transmit_heartbeat_msg()
            else:
                raise ValueError(
                    f'Replica is in invalid state:{self.curr_state}'
                )

    def handle_msg(self, msg: dict):
        # Indicates the msg is from a client
        if msg['type'] in ('get', 'put'):
            handle_client_msg(self, msg)
        # Indicates the msg is an RPC msg - all RPC msgs have terms
        elif msg['term'] < self.curr_term:
            # Ignore any messages coming from lower terms, these are out of
            # date
            self.log('Ignoring out of date or invalid msg')
        # Indicates the msg is another candidate requesting a vote
        elif msg['type'] == 'request_vote':
            handle_req_vote_msg(self, msg)
        # Indicates the msg is an incoming vote for our replica
        elif msg['type'] == 'vote_approval':
            handle_incoming_vote_msg(self, msg)
        # Indicates a heartbeat message / replicate log msg from a leader
        elif msg['type'] == 'append_entries':
            handle_append_entries_msg(self, msg)
        else:
            raise ValueError(f'Unknown msg type {msg["type"]} encountered')

    def check_heartbeat_timeout(self):
        curr_time : float = time.time()
        # If we have not received a heartbeat yet, trigger an election
        if curr_time - self.timer_start >= self.wait_time:
            self.log('Heartbeat timeout expired! Entering election mode')
            self.curr_term += 1  # Increment the current erm
            self.curr_state = 'candidate'  # Set ourself to a candidate
            # Forget any old leaders since we're entering a new term
            self.leader = 'FFFF'

            # Cast a vote for ourselves
            self.candidate_voted_for = self.id
            self.voters_this_term.add(self.id)

            # Send request vote RPCs to other replicas
            request_vote_msg : dict = {
                'type': 'request_vote',
                'src': self.id,
                'dst': BROADCAST,
                'leader': self.leader,
                'term': self.curr_term,
            }
            self.send(request_vote_msg)

            # Reset this candidate's election timer
            self.reset_heartbeat_timer()

    def transmit_heartbeat_msg(self):
        self.log('Transmitting heartbeat msg')
        heartbeat_msg = {
            'type': 'append_entries',
            'src': self.id,
            'dst': BROADCAST,
            'leader': self.id,
            'term': self.curr_term
        }
        self.send(heartbeat_msg)

    def reset_heartbeat_timer(self):
        self.log('Resetting heartbeat timer')
        # Create a timer in a random interval 150-300 MS
        self.timer_start = time.time()
        self.wait_time = random.randint(150, 300) / 1000

    def revert_to_follower(self, incoming_term : int):
        """
        Resets the state after this replica finds out about another replica
        with a higher term or after this replica receives an append entries
        message from a leader whose term is >= its current term
        """
        self.log('Discovered higher term or leader in current term, resetting '
                 'voting data')
        # Revert this replica to a follower
        self.curr_state = 'follower'
        # Update the term to reflect the discovered higher term
        self.curr_term = incoming_term
        # Reset any voting related information
        self.candidate_voted_for = None
        self.voters_this_term = set()
        self.leader = 'FFFF'
