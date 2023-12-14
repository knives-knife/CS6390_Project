
#region Imports
import os
import io
import time
import sys

from enum import Enum
from typing import List, Dict, Set, Tuple
from fileHelpers import * 

#endregion Imports


#region Constants

NUM_NODES: int = 10
RUN_MINUTES: int = 4
SLEEP_SECONDS: float = 1

HELLO_MESSAGE_REOCCURRENCE_SEC: float = 5
LSA_MESSAGE_REOCCURRENCE_SEC: float = 10
REFRESH_PARENT_MESSAGE_REOCCURRENCE_SEC: float = 10
MCAST_MESSAGE_REOCCURRENCE_SEC: float = 10

PRUNE_HELLO_REOCCURRENCE_SEC = 10
PRUNE_LSA_REOCCURRENCE_SEC = 30
PRUNE_JOIN_REOCCURRENCE_SEC = 10

LSA_THROWAWAY_TIME: float = 30

CWD: str = os.getcwd()
INPUT_DIR: str = CWD + "/input"
OUTPUT_DIR: str = CWD + "/output"
INPUT_FILEPATH: str = INPUT_DIR + "/input_"
OUTPUT_FILEPATH: str = OUTPUT_DIR + "/output_"

#endregion Constants


#region Classes

class mCastTypeEnum(Enum):
    NONE = 0
    RECEIVER = 1
    SENDER = 2

class NodeTime():
    def __init__(self, id: int) -> None:
        self.node = id
        self.time = time.time()

class LinkStateTableEntry():
    def __init__(self, ts: int, neighbors: List[int]) -> None:
        self.ts: int = ts
        self.neighbors: List[int] = neighbors

class mCastTableEntry():
    def __init__(self, parent: int, pathToSource: List[int], pathToParent: List[int]) -> None:
        self.parent: int = parent
        self.pathToSource: List[int] = pathToSource
        self.pathToParent: List[int] = pathToParent

    def __eq__(self, other) -> bool:
        return self.parent == other.parent and self.pathToSource == other.pathToSource and self.pathToParent == other.pathToSource
    
#endregion Classes        


#region Global Variables

nodeNum: int = -1
mCastType: mCastTypeEnum = mCastTypeEnum.NONE
listeningToSource: int = -1
dataMessage: str = ""

inputFile: io.TextIOWrapper = None
outputFile: io.TextIOWrapper = None

lastHelloMessageTime: float = -HELLO_MESSAGE_REOCCURRENCE_SEC
lastLSAMessageTime: float = -LSA_MESSAGE_REOCCURRENCE_SEC
lastRefreshParentMessageTime: float = -REFRESH_PARENT_MESSAGE_REOCCURRENCE_SEC
lastMCastMessageTime: float = -MCAST_MESSAGE_REOCCURRENCE_SEC

lastPruneHelloTime: float = time.time()
lastPruneLSATime: float = time.time()
lastPruneJoinTime: float = time.time()

lsaNum: int = 0
# Key is the node the LSA was received from
# Value is the LSA information
lsaTable: Dict[int, LinkStateTableEntry] = {}

# Row number indicates a node
# Row indicates the neighbors of the node
neighborTables: List[List[int]] = [[] for i in range(NUM_NODES)]
incomingNeighbors: Set[int] = set()

# Indicate that a node has sent a particular message
hellosReceivedFrom: Set[int] = set()
lsaReceivedFrom: Set[int] = set()
joinReceivedFor: Set[int] = set()

# Index is the TO node
# Value is the PARENT node
routingTable: List[int] = [-1 for node in range(NUM_NODES)]

# Key is the root node
# Value is the path information
mCastTable: Dict[int, mCastTableEntry] = {}

#endregion Global Variables


#region Helper Functions

def timeCheckPassed(lastTime: float, reoccurrenceTime: float) -> bool:
    """Determines whether an event should happen based on the last time it happened and how often it should happen.

    Args:
        lastTime (float): The last time the event occurred.
        reoccurrenceTime (float): How often the event should occurr.

    Returns:
        bool: True if the even should occurr. False, otherwise.
    """
    return (lastTime + reoccurrenceTime <= time.time())

def listToString(someList) -> str:
    """Converts list to a string delimited by space.

    Args:
        someList: List of items to be joined in the string.

    Returns:
        str: String with elements of someList joined with a space.
    """
    return " ".join([str(el) for el in someList])

def printUsage() -> None:
    """Prints the command line usage.
    """
    print("Usage: python3 node.py [nodeNumber: int] <(\"sender\"|\"recevier\"): str> <senderDataMessage: str/receiverSource: int>")
    exit()

def printState() -> None:
    """Prints information about the node.
    """

    print(f"\n\n\nSTATE OF NODE {nodeNum}: \n\n")

    print("INCOMING NEIGHBORS:")
    print(incomingNeighbors)

    print("\n\nLSA TABLE:")
    for node in lsaTable:
        print(f"{node}: {lsaTable[node].ts} {lsaTable[node].neighbors}")

    print("\n\nROUTING TABLE:")
    for i in range(len(routingTable)):
        print(f"TO: {i}\tPARENT: {routingTable[i]}")
    print(routingTable)

    print("\n\nMCAST TABLE:")
    for root in mCastTable:
        print(f"ROOT: {root}\tPARENT: {mCastTable[root].parent}\n"
              +
              f"\tSOURCE PATH: {mCastTable[root].pathToSource}\n"
              +
              f"\tPARENT PATH: {mCastTable[root].pathToParent}\n")

    print("\n\n")
    return

#endregion Helper Functions


#region Parent Structure

def getParentStructure(src: int) -> List[int]:
    """Modified BFS to get the parent structure from the neighbor tables.

    Args:
        src (int): The source that the paths will begin from.

    Returns:
        List[int]: Parent structure where index is is the TO node and value is the PARENT node.
    """
    dist: List[int] = [sys.maxsize * 2 + 1 for node in range(NUM_NODES)]
    q: List[int] = []
    parents: List[int] = [-1 for node in range(NUM_NODES)]

    dist[src] = 0
    q.append(src)

    while (len(q) > 0):
        u: int = q.pop()
        for v in neighborTables[u]:
            if (dist[v] > dist[u] + 1):
                dist[v] = dist[u] + 1
                q.append(v)
                parents[v] = u
    return parents

def getPathFromParentStructue(parents: List[int], src: int, dst: int) -> List[int]:
    """Get the path to the destination from the parent structure. 

    Args:
        parents (List[int]): List of parents on the path to the destination.
        src (int): Source the path will begin from.
        dst (int): Desination the path will end on.

    Returns:
        List[int]: If there exists a path, path from src to dst including both src and dst is returned. Otherwise, None.
    """
    path: List[int] = []
    count: int = 0
    length: int = len(parents)
    currParent = parents[dst]
    # There is no known parent to the destination
    if (currParent == -1):
        return None
    # Build path until node with no known parent is found
    while (currParent != -1):
        path.insert(0, currParent)
        currParent = parents[currParent]
        # Ensure path construction will terminate
        if (count > length):
            return None
        count += 1
    # A path to the src is not possible
    if (path[0] != src):
        return None
    
    path.append(dst)

    # print(f"PATH FROM {src} TO {dst}:")
    # print(path)
    return path

def findPath(src: int, dst: int) -> List[int]:
    """Finds shortest path from src to dst.

    Args:
        src (int): The source node.
        dst (int): The destination node.

    Returns:
        List[int]: If there exists a path, the shortest path from src to dst including both src and dst is returned. Otherwise, None.
    """

    # If the source is non-existant, don't try to find a path
    if (src == -1):
        return None

    # If the source is this node, use the Routing Table
    # as the parent structure and get the path from the 
    # source to the destination
    if (src == nodeNum):
        return getPathFromParentStructue(routingTable, src, dst)
    
    # Otherwise, create a new parent structure based at the source
    parents = getParentStructure(src)

    # print("\n\nPARENT STRUCTURE:")
    # for i in range(len(parents)):
    #     print(f"TO: {i}\tPARENT: {parents[i]}")
    # print(parents)
    
    # Get the path from the source to the destination 
    # using the parent structure just created
    return getPathFromParentStructue(parents, src, dst)

def buildRoutingTable() -> None:
    """Build the routing table. The routing table is a parent structure rooted at this node.
    """
    global routingTable

    # Use the parent struture base at this node 
    # as the Routing Table
    routingTable = getParentStructure(nodeNum)

#endregion Parent Structure


#region Update Tables

def updateNeighborTablesFromNode(node: int, updateRoutingTable: bool) -> None:
    """Updates neighbor tables based on only one entry in the linkstate advertisement table.

    Args:
        node (int): Node number with linkstate advertisement to update the neighbor tables.
    """
    global neighborTables


    if (lsaTable.get(node) is not None):
        # Look at each incoming neighbor listed in the LSA
        for incNeighbor in lsaTable[node].neighbors:
            # If this node is not listed in the Neightbor Table
            # of the incoming neighbor, then add it
            if (node not in neighborTables[incNeighbor]):
                neighborTables[incNeighbor].append(node)

    # Update Routing Table if this is the only node being update
    # Otherwise, don't
    if (updateRoutingTable):
        buildRoutingTable()
    
    return

def updateNeighborTablesFromNodeNeighbors(node: int, neighbors: List[int], updateRoutingTable: bool):
    """Removes node information from the neighbor tables.

    Args:
        node (int): Node number being removed.
        neighbors (List[int]): List of neighbors nodes of the node being removed.
        updateRoutingTable (bool): True if the routing table should be updated. False, otherwise.
    """

    # Remove the node from the Neighbor Tables of the neighbors given 
    for neighbor in neighbors:
        neighborTables[neighbor].remove(node)
    
    # Update Routing Table if this is the only node being update
    # Otherwise, don't
    if (updateRoutingTable):
        buildRoutingTable()

    return

def updateNeighborTables() -> None:
    """Updates neighbor tables based on all entries in the linkstate advertisement table.
    """

    # Update the Neighbor Tables for each node that this node
    # has heard an LSA from
    for node in lsaTable:
        updateNeighborTablesFromNode(node, False)
    
    # Update the Routing Table after all Neighbor Tables are updated
    buildRoutingTable()
    return

#endregion Update Tables


#region MCast Functions

def getMCastTableEntry(mCastRoot: int, mCastListener: int) -> mCastTableEntry:
    """Finds the path from the root to the listener and the path from the listener to the parent of the listener on the root-to-listener path.

    Args:
        mCastSource (int): The root of the tree where data comes from.
        mCastListener (int): The node that wishes to listen to the root.

    Returns:
        mCastTableEntry: The information to listen to the root.
    """
    # Check for path to source
    sourcePath = findPath(mCastRoot, mCastListener)
    # If none, return (need more topology info first)
    if (sourcePath is None):
        # print(f"MCAST TREE - SOURCE PATH NOT FOUND: {mCastRoot} TO {mCastListener} ")
        return None
    # Parent is the second to last in the path from mCastRoot to mCastListener
    parent: int = sourcePath[-2]

    # If the parent is the same as the root, don't bother finding a 
    # parent path since this node can alread hear from the root
    if (parent == mCastRoot):
        return mCastTableEntry(parent, sourcePath, [])
    # Otherwise, compute the parent path (the path from the mCastListener to the parent)
    parentPath = findPath(mCastListener, parent)

    # If there is no parent path, then this node can't join the tree
    if (parentPath is None):
        # print(f"MCAST TREE - PARENT PATH NOT FOUND: {mCastListener} TO {parent}")
        return None
    # Return the information to listen to the root
    return mCastTableEntry(parent, sourcePath, parentPath)

def updateMCastTableForRoot(root: int) -> int:
    """Updates the MCast Table with the latest information for a single root.

    Args:
        root (int): The root to be updated.

    Returns:
        int: If there is no way for the node to hear from the root, then the root is returned. Otherwise, there is a way to hear the root, so -1 is returned.
    """

    # See if this node has paths to join the tree
    mCastEntry = getMCastTableEntry(root, nodeNum)

    # If it doesnt, return the root number
    if (mCastEntry is None):
        return root
    
    # Otherwise, add this root to the MCast Table 
    # with the path information
    mCastTable[root] = mCastEntry

    # TODO - REMOVE
    # sourcePath = findPath(sender, nodeNum)
    # if (sourcePath is None):
    #     print(f"NO MORE PATH FOR ROOT, {sender}, TO ME, {nodeNum}")
    #     return sender

    # if (len(mCastTable[sender].pathToSource) > len(sourcePath)):
    #     mCastTable[sender].pathToSource = sourcePath

    # parent: int = mCastTable[sender].pathToSource[-2]
    # mCastTable[sender].parent = parent

    # parentPath = findPath(nodeNum, parent)
    # if (parentPath is None):
    #     print(f"NO MORE PATH FOR ME, {nodeNum}, TO PARENT, {parent}")
    #     return sender
        
    # if (len(mCastTable[sender].pathToParent) <= len(parentPath)):
    #     mCastTable[sender].pathToParent = parentPath

    # Return -1 indicating this node has path information to the root
    return -1

def updateMCastTable() -> None:
    """Update all the roots in the MCast Table with the latest information. Removes any root that cannot be reached.
    """
    # Iterate through each root in the MCast Table
    removeRootList: List[int] = []
    for root in mCastTable.keys():
        # If there isn't path information to get to 
        # join the tree, then mark the root to be removed
        rootToRemove = updateMCastTableForRoot(root)
        if (rootToRemove > -1):
            removeRootList.append(rootToRemove)

    # Remove the marked roots
    for root in removeRootList:
        mCastTable.pop(root)
    
    return

#endregion MCast Functions


#region Send Messages

def sendJoinMessageForMCastEntry(root: int, mCastEntry: mCastTableEntry) -> None:
    """Sends a JOIN message if a JOIN message is required.

    Args:
        root (int): The root of the tree.
        mCastEntry (mCastTableEntry): The corresponding MCast Entry to the root.
    """
    # Don't send JOIN message if the parent is the root since this node can already
    # hear the root
    if (mCastEntry.parent == root):
        return
    
    parent: int = mCastEntry.parent
    pathToParent: List[int] = mCastEntry.pathToParent
    # print(f"JOINING/REFRESHING TREE ROOTED AT {listeningToSource} WITH PARENT {parent}")
    writeToFile(outputFile, [f"join {nodeNum} {root} {parent} {listToString(pathToParent[1:-1])}\n"])
    return

def sendHelloMessage() -> None:
    """Sends HELLO message.
    """
    global lastHelloMessageTime
    if (timeCheckPassed(lastHelloMessageTime, HELLO_MESSAGE_REOCCURRENCE_SEC)):
        # print("SENDING HELLO")
        writeToFile(outputFile, [f"hello {nodeNum}\n"])
        lastHelloMessageTime = time.time()
    return

def sendLSAMessage() -> None:
    """Send Link State Advertisement message.
    """
    global lsaNum
    global lastLSAMessageTime
    if (timeCheckPassed(lastLSAMessageTime, LSA_MESSAGE_REOCCURRENCE_SEC)):
        # print("SENDING LSA")
        writeToFile(outputFile, [f"linkstate {nodeNum} {lsaNum} {listToString(list(incomingNeighbors))}\n"])
        lsaNum += 1
        lastLSAMessageTime = time.time()
    return

def sendJoinMessage() -> None:
    """Sends JOIN message to parent on the SPT of the source and sends JOIN messages to each parent in the MCast Table.
    """
    
    global lastRefreshParentMessageTime
    if (timeCheckPassed(lastRefreshParentMessageTime, REFRESH_PARENT_MESSAGE_REOCCURRENCE_SEC)):
        
        # If this node is a receiver, attempt to find a path to join the tree
        if (mCastType == mCastTypeEnum.RECEIVER):
            mCastEntry = getMCastTableEntry(listeningToSource, nodeNum)

            # If path information was found, send a join message to this
            # node's parent on the tree
            if (mCastEntry is not None):
                sendJoinMessageForMCastEntry(listeningToSource, mCastEntry)
                
        # Update the MCast Table before sending refresh messages
        updateMCastTable()
        for root in mCastTable.keys():
            sendJoinMessageForMCastEntry(root, mCastTable[root])

        lastRefreshParentMessageTime = time.time()
        
    return

def sendMCastMessage() -> None:
    """Send DATA message to receivers.
    """
    global lastMCastMessageTime
    # If mCastType is SENDER, send DATA message 
    if (mCastType == mCastTypeEnum.SENDER):
        if (timeCheckPassed(lastMCastMessageTime, MCAST_MESSAGE_REOCCURRENCE_SEC)):
            # print("SENDING MCAST MESSAGE")
            writeToFile(outputFile, [f"data {nodeNum} {nodeNum} {dataMessage}\n"])
            lastMCastMessageTime = time.time()
    return

#endregion Send Messages


#region Handle Message Types

def handleHelloMessage(id: int) -> None:
    """Adds a node to the incoming neighbors.

    Args:
        id (int): Node to be added.
    """

    # Mark the node as having received a HELLO message from
    hellosReceivedFrom.add(id)

    # If the node is not in this node's incoming neighbors
    # add it and add it to this node's  Neighbor Table as well
    if (id not in incomingNeighbors):
        # print(f"ADDING {id} TO INC NEIGHBORS")
        incomingNeighbors.add(id)
        neighborTables[id].append(nodeNum)        
        
    return

def handleLSAMessage(id: int, ts: int, incNeighbors: List[int]) -> None:
    """Add the LSA information to the LSA table.

    Args:
        id (int): The node that sent the LSA.
        ts (int): The time stamp of the LSA.
        incNeighbors (List[int]): List of incoming neighbors of the sending node.
    """

    # Don't forward your own LSA received from neighbors
    if (id == nodeNum):
        return

    # Mark the node as having received an LSA message from
    lsaReceivedFrom.add(id)

    # If this node does not have an LSA Table entry for the id node, 
    # or if the LSA is a newer LSA than this node has, forward it and
    # update this node's Neightbor Tables
    if ((lsaTable.get(id) is None) or (lsaTable[id].ts < ts)):
        writeToFile(outputFile, [f"linkstate {id} {ts} {listToString(incNeighbors)}\n"])

        # print(f"ADDING/UPDATING LSA ENTRY FOR {id}")
        lsaTable[id] = LinkStateTableEntry(ts, incNeighbors)
        updateNeighborTablesFromNode(id, True)

    return

def handleJoinMessage(id: int, sid: int, pid: int, intermediateNodes: List[int]) -> None: 
    """Add MCast information into the MCast Table or forward the join message.

    Args:
        id (int): The ID of the node wiishing to join.
        sid (int): The ID of the root of the tree.
        pid (int): The ID of the parent od the node wishing to join.
        intermediateNodes (List[int]): The intermediate nodes from the node wishing to join to the parent. 
    """
    # This node is the root
    if (nodeNum == sid):
        # Don't do anything since the source is already on the tree
        return


    # This node is the parent
    if (nodeNum == pid):
        # Mark this root as refreshed
        joinReceivedFor.add(sid)
        
        # If root is alread registered in the MCast Table 
        # update the MCast Table entry for it
        # Don't need to send refresh since sendJoinMessage handles that
        if (sid in mCastTable.keys()):
            # print(f"UPDATING MCAST TABLE ENTRY FOR ROOT {sid}")
            updateMCastTableForRoot(sid)
            return   
        
        # Get the information needed to source there
        mCastEntry = getMCastTableEntry(sid, nodeNum)
        if (mCastEntry is not None):
            # Add to registered sourced
            # print(f"ADDING MCAST TABLE ENTRY FOR ROOT {sid}")
            mCastTable[sid] = mCastEntry
            # Send join to my parent in the tree
            sendJoinMessageForMCastEntry(sid, mCastEntry)
        return

    # If this node is the next in the list to send, forward the message
    if (len(intermediateNodes) > 0 and nodeNum == intermediateNodes[0]):
        writeToFile(outputFile, [f"join {id} {sid} {pid} {listToString(intermediateNodes[1:])}\n"])
        return

    return

def handleDataMessage(sender: int, root: int, dataMess: str):
    """Forwards the DATA message if the sender is this node's parend on the tree.

    Args:
        sender (int): The node that is forwarding the message.
        root (int): The root of the tree.
        dataMess (str): The message from the root of the tree.
    """
    # This node is not in the root's tree
    if (root not in mCastTable.keys()):
        return
    
    # The sender is this node's parent on the tree
    if (sender == mCastTable[root].parent):
        # Forward the message
        writeToFile(outputFile, [f"data {nodeNum} {root} {dataMess}\n"])

    return

def handleMessages() -> None:
    """Reads from the input file, parses the message, and hands the message off to the appropriate handler.
    """
    newLines = inputFile.readlines()
    
    # Nothing new
    if (len(newLines) < 1):
        return
    
    # For each new message, parse the message and hand the message off to the correct handler
    for line in newLines:
        message = line.split()
        messType: str = message[0]
        if (messType == "hello"):
            handleHelloMessage(int(message[1]))
        elif (messType == "linkstate"):
            try:
                handleLSAMessage(int(message[1]), int(message[2]), [int(strId) for strId in message[3:]])
            except IndexError:
                handleLSAMessage(int(message[1]), int(message[2]), [])
        elif (messType == "join"):
            try:
                handleJoinMessage(int(message[1]), int(message[2]), int(message[3]), [int(strId) for strId in message[4:]])
            except IndexError:
                handleJoinMessage(int(message[1]), int(message[2]), int(message[3]), [])
        elif (messType == "data"):
            handleDataMessage(int(message[1]), int(message[2]), listToString(message[3:]))
        else:
            print("COULD NOT PARSE MESSAGE")
    return

#endregion Handle Message Types


#region Prune

def pruneHello() -> None:
    """Removes nodes from incoming neighbors if they haven't been heard from recently.
    """
    global hellosReceivedFrom
    global lastPruneHelloTime
    if (timeCheckPassed(lastPruneHelloTime, PRUNE_HELLO_REOCCURRENCE_SEC)):
        # print("PRUNING INCOMING NEIGHBORS")
        remove: List[int] = []
        # Check if received HELLO from the node's known incoming neighbors
        # If not, add the node to the removing list
        for incNeighbor in incomingNeighbors:
            if (incNeighbor not in hellosReceivedFrom):
                remove.append(incNeighbor)
        if (len(remove) > 0):
            # Remove the neighbors from the node's known incoming neighbors
            for node in remove:
                # print(f"REMOVING INC NEIGHBOR {node}")
                incomingNeighbors.discard(node)
        # Reset the received from set and timer
        hellosReceivedFrom.clear()
        lastPruneHelloTime = time.time()
    return

def pruneLSA() -> None:
    """Removes LSA entries from LSA table if the nodes haven't been heard from recently.
    """
    global lsaReceivedFrom
    global lastPruneLSATime
    if (timeCheckPassed(lastPruneLSATime, PRUNE_LSA_REOCCURRENCE_SEC)):
        # print("PRUNING LSA TABLE")
        remove: List[int] = []
        # Check if received LSA from the node's known LSA entries
        # If not, add the node to the removing list
        for node in lsaTable:
            if (node not in lsaReceivedFrom):
                remove.append(node)
        if (len(remove) > 0):
            # Update the neighbor tables 
            # Remove the LSA entries from the node's known LSA entries
            for node in remove:
                # print(f"REMOVING LSA ENTRY {node}")
                updateNeighborTablesFromNodeNeighbors(node, lsaTable[node].neighbors, False)
                lsaTable.pop(node)
        # Reset the received from set and timer
        lsaReceivedFrom.clear()
        lastPruneLSATime = time.time()
    return

def pruneJoin() -> None:
    """Removes MCast Table entries from the MCast Table if a JOIN message has not been received recently.
    """
    global joinReceivedFor
    global lastPruneJoinTime
    if (timeCheckPassed(lastPruneJoinTime, PRUNE_JOIN_REOCCURRENCE_SEC)):
        # print("PRUNING MCAST TABLE")
        remove: List[int] = []
        # Check if received join for the roots in the MCast table
        # If not, add the node to the removing list
        for root in mCastTable.keys():
            if (root not in joinReceivedFor):
                remove.append(root)
        if (len(remove) > 0):
            # Remove the tree information
            for root in remove:
                # print(f"REMOVED {root} FROM MCAST TABLE")
                mCastTable.pop(root)
        # Reset the received for set and timer
        joinReceivedFor.clear()
        lastPruneJoinTime = time.time()
    return

def prune() -> None:
    """Call all pruning functions.
    """
    pruneHello()
    pruneLSA()
    pruneJoin()
    return

#endregion Prune


#region Drivers

def initialize() -> None:
    """Take the command line arguments and set appropriate variables.
    """
    if (len(sys.argv) < 2):
        printUsage()

    global nodeNum
    global mCastType
    global listeningToSource
    global dataMessage
    global inputFile
    global outputFile

    # Node number stored in the first argument
    nodeNum = int(sys.argv[1])

    # If there is a second argument, set the node's multicast type
    try:
        if (sys.argv[2].lower() == "sender"):
            mCastType = mCastTypeEnum.SENDER
        elif (sys.argv[2].lower() == "receiver"):
            mCastType = mCastTypeEnum.RECEIVER
        else:
            printUsage()
    except IndexError:
        pass
    
    # If the node is a receiver, set the source to the third argument
    if (mCastType == mCastTypeEnum.RECEIVER):
        try:
            listeningToSource = int(sys.argv[3])
            if (listeningToSource > NUM_NODES-1):
                print(f"receiverParent too large - Must be 0 to {NUM_NODES-1}")
        except (IndexError, ValueError, TypeError):
            printUsage()
    # If the node is a sender (a root), set the data message to the third argument
    elif (mCastType == mCastTypeEnum.SENDER):
        try:
            dataMessage = sys.argv[3]
        except IndexError:
            printUsage()

    # Open the IO files
    inputFile = openReadOnlyFile(f"{INPUT_FILEPATH}{nodeNum}.txt")
    outputFile = openAppendFile(f"{OUTPUT_FILEPATH}{nodeNum}.txt")

    # print(f"INPUT FILE: {inputFile}")
    # print(f"OUTPUT FILE: {outputFile}")

    # Throw away anything that was sent before the node started up
    _ = inputFile.readlines()



    return

def participate() -> None:
    """Start the link state protocol. Runs for RUN_MINUTES minutes. 
    """
    # print("NODE NUM: " + str(nodeNum))
    endTime = time.time() + 60 * RUN_MINUTES
    while (time.time() < endTime):
        sendHelloMessage()
        sendLSAMessage()
        sendJoinMessage()
        sendMCastMessage()
        handleMessages()
        prune()

        time.sleep(SLEEP_SECONDS)
    return

def tearDown() -> None:
    """Clean up the node before exiting.
    """
    outputFile.close()
    inputFile.close()

def main():
    initialize()
    try:
        participate()
    except KeyboardInterrupt:
        pass
    # printState()
    tearDown()
    return
    
#endregion Drivers





if (__name__ == "__main__"):
    main()
