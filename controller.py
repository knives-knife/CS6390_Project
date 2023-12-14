
#region Imports

import datetime
import os;
import io
import time;

from typing import List, Dict
from fileHelpers import * 

#endregion Imports


#region Constants

NUM_NODES = 10
RUN_MINUTES = 5
CHECK_MESSAGES_SECONDS = 0.5

CWD = os.getcwd()
INPUT_DIR = CWD + "/input"
OUTPUT_DIR = CWD + "/output"
INPUT_FILEPATH = INPUT_DIR + "/input_"
OUTPUT_FILEPATH = OUTPUT_DIR + "/output_"

#endregion Constants


#region Global Variables

inputFiles: List[io.TextIOWrapper] = []
outputFiles: List[io.TextIOWrapper] = []

neighborTables: List[List[int]] = [[] for i in range(NUM_NODES)]

#endregion Global Variables


#region File Handling

def clearOldFiles() -> None:
    print("Clearing Old Files...")
    makeDirectory(INPUT_DIR)
    makeDirectory(OUTPUT_DIR)
    clearDirectory(INPUT_DIR)
    clearDirectory(OUTPUT_DIR)
    print("Old Files Cleared!")
    return

def makeNewFiles() -> None:
    print("Making New Files...")
    for nodeNum in range(NUM_NODES):
        makeFile(f"{INPUT_FILEPATH}{nodeNum}.txt")
        makeFile(f"{OUTPUT_FILEPATH}{nodeNum}.txt")
    print("New Files Made!")
    return

def openFiles() -> None:
    for nodeNum in range(NUM_NODES):
        inputFiles.append(openAppendFile(f"{INPUT_FILEPATH}{nodeNum}.txt"))
        outputFiles.append(openReadOnlyFile(f"{OUTPUT_FILEPATH}{nodeNum}.txt"))
    return

def closeFiles() -> None:
    for file in inputFiles:
        file.close()
    for file in outputFiles:
        file.close()
    return

#endregion File Handling


#region Topology

def fillNeighborTables() -> None:
    """Read the topology file and fill the Neighbor Tables.
    """
    topoologyFile = open(CWD + "/topology", "r")
    for line in topoologyFile.readlines():
        channel = line.split()
        neighborTables[int(channel[0])].append(int(channel[1]))
    return

#endregion Topology


#region Message Forwarding

def checkNewMessages() -> Dict[int, List[str]]:
    """Check for new messaged from all nodes.

    Returns:
        Dict[int, List[str]]: The keys are the nodes that have new messages. The value is the list of new messages.
    """
    newNodeMessages = {}

    # Look at each node's output file and see if there are new lines
    for nodeNum in range(NUM_NODES):
        newLines = outputFiles[nodeNum].readlines()
        # If new lines are found, add the node to the return dictionary
        if (len(newLines) > 0):
            # print("Found New Lines In " + str(nodeNum))
            newNodeMessages[nodeNum] = newLines
    return newNodeMessages

def forwardToNeighbors(nodeNum: int, messages: List[str]) -> None:
    # For each neighbor of the node, write to the neighbor's input file
    for neighbor in neighborTables[nodeNum]:
        # print(f"Writing to Node {neighbor}...")
        writeToFile(inputFiles[neighbor], messages)
    return

def forwardMessages() -> None:
    endTime = time.time() + 60 * RUN_MINUTES
    while (time.time() < endTime):
        # Check for new messaged
        # If new messages are found, forward the messages
        # to the node's neighbors
        newMessages = checkNewMessages()
        if len(newMessages) > 0:
            # print(newMessages)
            for nodeNum in newMessages.keys():
                forwardToNeighbors(nodeNum, newMessages[nodeNum])
        time.sleep(CHECK_MESSAGES_SECONDS)
    return

#endregion Message Forwarding


#region Driver

def main():
    clearOldFiles()
    makeNewFiles()
    fillNeighborTables()
    openFiles()
    try:
        forwardMessages()
    except KeyboardInterrupt:
        pass
    closeFiles()
    return

#endregion Driver


if (__name__ == "__main__"):
    main()