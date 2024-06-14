# 3700_Key-Value_Database
## High Level Approach
- We decomposed replica state data into 4 main parts in order to handle modifying replica server state
based on new information learned from incoming messages 
1. **State Data** (required for the servers to communciate and respond to new state information), never shared with other servers
   - The UDP socket connection to the lAN 
   - The unique ID of each server 
   - The list of `others` (ids) of the other servers
   - The current state of the server (follower, candidate, or leader)
   - The heartbeat receiving timer (for non-leaders) and the heartbeat transmission timer (for leaders)
2. **Voting Data** (used for determining how to vote in elections, dynamically changes often)
   - The candidate voted for this term
   - The current term 
   - The leader 
   - The ids of voters this term (if the server is a candidate)
3. **State Machine Data** (keeps track of each server's datastore, the information clients read & modify for the distributed system)
   - The datastore (key-value) mapping that clients request to modify and read 
   - The entry log (consists of client requests, some of which are applied to the state machine and some of which are pending application)
   - The commit index -> the index of the highest log entry applied to the state machine 
4. **Whole System Data** (used by the leader to learn about other servers' states)
   - The next index to send map (the index of the next log entry to send to each server)
   - The acked index map (highest log entry known to be replicated on each follower server)
- We separated out responsibilites for incoming message (either remote procedure call or client message) handling into distinct modules
1. **client_msg_handler.py**-> deciphers requests from the client, delegates to state machine modifiers as necessary, and returns responses to the client 
2. **election_msg_handler.py**-> contains logic for server-server voting communications, including vote collection and replica state transitions
3. **append_entries_msg_handler** -> handles sending / receiving of log replication from leader to followers, contains logic for appending entries in response to log replication requests
## Strategy that our program implements
- We used an event-driven approach to implement our replica servers to adhere
to the RAFT protocol:
  - We constantly monitored our socket connection to the LAN for incoming remote procedure calls and client messages 
via the `select` syscall
  - If there are new messages (indicated by a readable socket returned by the `select` call), we delegated the handling 
  of the message based on the type of the message (ex. vote requests, log replication, client requests, etc.)
  - Each time we checked for a message, whether we received a new message and handled it, or there were no readable sockets, 
we monitored our various timeouts based on replica states 
  - We ensured any replicas in follower or candidate state triggered an election if they went too long without 
receiving a log replication message from the leader
  - We ensured any replicas in leader state were transmitting log replication messages frequently enough so that all 
followers would be aware of that the leader server was still alive
- We added terms to our custom RPCs in order to identify obsolete information, due to network unreliability, as well as 
to establish a logical ordering of events
## Challenges Faced
- **Understanding RAFT**
  - We struggled to understand the contribution of each phase of RAFT to the main goal of consensus 
  - The official RAFT paper as well as the UIUC RAFT slides helped break it down for us 
- **Dealing with randomness** 
  - Due to the random nature of the simulator, sometimes tests would pass locally but not in the autograder
and vice versa. This led to some false positives in which we thought our code achieved certain functionality when
it in fact did not
  - In order to deal with this, we will run multiple tests at once going forward in order to ensure any changes 
are backwards compatible with previously required functionality 
- **Parsing test output** 
  - Due to the sheer volume of messages sent between replicas, even with logging it was difficult to trace through 
test cases to figure exactly where our code went wrong. We tried limiting what was displayed in the log, however it 
still got a little overwhelming. Going forward, when developing projects at this scale, we will 
try to test more often after intermittent changes. 
- **Decomposing the components of RAFT**
  - Since RAFT is a complicated and multiphase protocol, it was difficult to come up with an implementation plan that supported 
incremental progress and milestone functionalities. Even with a suggested implementation strategy, the leaps between 
certain milestone felt a little overwhelming at times. To address this in the future, we will try to break down milestones
into sub-milestones themselves.
## Testing Overview
- **Logging mechanisms**
  - We originally wrote logs to debug files, having each replica dump its logging information 
into its own file per run of our database 
  - In order to better observe the entire system state together, we ended 
up combining the logs into one file, but have each log specify which replica server
it is logging for 
  - For each test, we inspected the log output like this: 
  - `python ./run ./configs<test_name> > output.txt`
