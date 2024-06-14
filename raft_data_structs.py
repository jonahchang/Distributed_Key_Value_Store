class LogEntry:
    """
    Represents a log entry in a replica's log.
    Log entry -> encapsulates a message and term
    msg (dict)-> Contains the message ID and the client operation we are
    performing (GET or PUT)
    term (int)-> the term # of replica r when this entry is added to r's log
    """
    def __init__(self, msg: dict, term: int):
        self.msg = msg
        self.term = term
