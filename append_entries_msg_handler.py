import Replica


def handle_append_entries_msg(replica: Replica, msg: dict):
    # If the leader's term is at least as large as current term,
    # recognize the leader as our leader and revert to follower state
    if msg['term'] >= replica.curr_term:
        replica.revert_to_follower(msg['term'])
        replica.leader = msg['leader']
        replica.reset_heartbeat_timer()
    else:  # Ignore any message from lower terms
        # Reject the RPC and remain in current state
        return
