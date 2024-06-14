import Replica
from raft_data_structs import LogEntry


def handle_client_msg(replica: Replica, msg: dict):
    # If we have not yet selected a leader, send a fail response
    if replica.leader == 'FFFF':
        send_fail_response(replica, msg)
    # If we have elected a leader and we are the leader, we can do the client
    # operation
    elif replica.leader == replica.id:
        initiate_client_operation(replica, msg)
    else:  # If we are not the leader, redirect to our leader
        send_redirect_response(replica, msg)


def initiate_client_operation(replica: Replica, msg: dict):
    # For GET requests, there is no state that must be modified or entry
    # appending to be done to the leader's log
    if msg['type'] == 'get':
        perform_get_operation(replica, msg)
        return
    # If we are here, we have a PUT operation request
    # Append an entry for the client request to the leader's log
    entry = LogEntry(msg, replica.curr_term)
    replica.entry_log.append(entry)

    apply_put_to_state_machine(replica, msg)
    return


def apply_put_to_state_machine(replica: Replica, msg: dict):
    """
    Applies the client entry PUT request to the given replica's state machine,
    returning the result of the PUT request to the client
    """
    key = msg['key']
    value = msg['value']
    replica.datastore[key] = value
    put_response = {
        'src': replica.id,
        'dst': msg['src'],
        'type': 'ok',
        'MID': msg['MID'],
        'term': replica.curr_term,
        'leader': replica.leader,
    }
    replica.send(put_response)


def perform_get_operation(replica, msg):
    """
    Invariant: replica is a leader
    """
    # For GET requests, since we are the leader, we can simply return the entry
    # in our datastore
    # If the entry exists, retrieve the entry from our datastore
    # Otherwise, represent the value of the entry as an empty string
    datastore_entry = ''
    if msg['key'] in replica.datastore.keys():
        datastore_entry = replica.datastore[msg['key']]
    get_response = {
        'src': replica.id,
        'dst': msg['src'],
        'type': 'ok',
        'MID': msg['MID'],
        'term': replica.curr_term,
        'leader': replica.leader,
        'value': datastore_entry
    }
    replica.send(get_response)


def send_redirect_response(replica: Replica, msg: dict):
    redirect_msg = {
        'type': 'redirect',
        'src': replica.id,
        'dst': msg['src'],
        'leader': replica.leader,
        'MID': msg['MID']
    }
    replica.send(redirect_msg)


def send_fail_response(replica: Replica, msg: dict):
    fail_msg = {
        'type': 'fail',
        'src': replica.id,
        'dst': msg['src'],
        'leader': replica.leader,
        'MID': msg['MID'],
    }
    replica.send(fail_msg)
