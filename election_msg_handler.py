import math
import Replica


def handle_req_vote_msg(replica: Replica, msg: dict):
    incoming_term: int = msg['term']
    # Ignore any vote request messages from earlier terms
    if incoming_term < replica.curr_term:
        return
    # If we discover a message from a higher term, we can revert to a
    # follower and update our term to the higher term
    if incoming_term > replica.curr_term:
        replica.revert_to_follower(incoming_term)
    # If we are here, the replica's term now matches the vote req's curr term
    # Grant the vote request if and only if...
    #   - We have not yet voted this term, or we already voted this candidate
    #   (we can notify them again we have voted for them)
    #   - The candidate requesting a vote's log is up to date
    candidate_id: str = msg['src']
    can_vote: bool = replica.candidate_voted_for in (candidate_id, None)
    if can_vote and is_valid_log(replica, msg):
        # Cast our vote for the requesting candidate
        grant_vote_req(replica, candidate_id)
    else:
        # If we cannot vote for the requesting candidate, simply return
        return


def handle_incoming_vote_msg(replica: Replica, msg: dict):
    incoming_term : int = msg['term']
    # We will ignore any vote request msgs from earlier terms
    if incoming_term < replica.curr_term:
        return
    if incoming_term > replica.curr_term:
        replica.revert_to_follower(incoming_term)
        # If the replica just reverted to a follower, then it cannot receive
        # any votes - we can simply return
        return
    if replica.curr_state != 'candidate':
        return

    # If we are here, the incoming the destination of the vote is an eligible
    # candidate for the requesting term - we can apply the vote

    # Add the voting replica to the replica's set of voters
    # Since the voter list is a set, if they already voted for us, it will
    # only get added once
    replica.voters_this_term.add(msg['src'])

    # Check if the replica has received a quorum
    total_replica_count : int = len(replica.others) + 1
    quorum : int = (total_replica_count // 2) + 1
    # If the replica has received a quorum, elect it as leader
    if len(replica.voters_this_term) >= quorum:
        replica.curr_state = 'leader'
        replica.leader = replica.id
        replica.transmit_heartbeat_msg()


def is_valid_log(replica: Replica, msg: dict):
    return True


def grant_vote_req(replica: Replica, candidate_id: str):
    replica.log(f'Granting vote request to candidate {candidate_id}')
    vote_msg : dict = {
        'type': 'vote_approval',
        'src': replica.id,
        'dst': candidate_id,
        # INVARIANT: If we are granting a vote req, the leader must be unknown
        'leader': 'FFFF',
        'term': replica.curr_term
    }
    # Update the replica's voted-for candidate for this term
    replica.candidate_voted_for = candidate_id
    # Send the vote approval message
    replica.send(vote_msg)
