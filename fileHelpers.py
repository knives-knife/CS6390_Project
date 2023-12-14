import io
import os;
import shutil
from typing import List;

def makeDirectory(folder: str) -> None:
    """Make a directory.

    Args:
        folder (str): Name for the directory to be made.
    """
    if (os.path.exists(folder) and os.path.isdir(folder)):
        return
    os.mkdir(folder)
    return

def clearDirectory(folder: str) -> None:
    """Removes everything in a directory.

    Args:
        folder (str): Name of the directory to be cleared.
    """
    for filename in os.listdir(folder):
        if (filename.startswith(".")):
            continue
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    return



def makeFile(file_path: str) -> None:
    """Makes a file.

    Args:
        file_path (str): The file path of the file to be made.
    """
    file = open(file_path, "x")
    file.close()
    return

def openReadOnlyFile(file_path: str) -> io.TextIOWrapper:
    """Open a file in read only mode.

    Args:
        file_path (str): The file path of the file to be opened.

    Returns:
        io.TextIOWrapper: The file descriptor for the opened file.
    """
    return open(file_path, "r")

def openAppendFile(file_path: str) -> io.TextIOWrapper:
    """Open a file in write only mode.

    Args:
        file_path (str): The file path of the file to be opened.

    Returns:
        io.TextIOWrapper: The file descriptor for the opened file.
    """
    return open(file_path, "a")

def writeToFile(file: io.TextIOWrapper, messages: List[str]) -> None:
    """Writes to a file.

    Args:
        file (io.TextIOWrapper): File descriptor to be written to.
        messages (List[str]): List of messages to write to the file.
    """
    file.writelines(messages)
    file.flush()
    return
