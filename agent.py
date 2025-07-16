# Agent python file to be ran on a given agent (Currently designed to run on Linux)

import requests 
import time 
import hashlib
import random 
#Import the beautiful soup python library to parse HTML files

class pythonAgent(): 

    def __init__(self, domain = None ):
        """Agent class:
            domain - domain that the agent references
            endpoint - the given endpoint that a given agent references

            """
        
        self.domain = domain  
        self.endpoint = None


def make_request(self):
    '''Takes a request to the currently set web server'''
    r = requests.get(self.domain)
    return r.text

def extract_html(): 
    '''Extracts given commands from the HTML including any updates to domain and more'''
    #Takes HTML file as an input
    # Read through the HTML file: 
        #parses: 
        # commands
        # domain currently being used
        # updates to how the commands will be encoded?? 
    #Returns the output of these, or simply updates them as currently variables in the class  


def execute_command(): 
    '''Executes the recieved command that is provided through parsing the html'''
    pass



if __name__ == "__main__": 
    while True: #While loop which constantly runs the requests for a given command
        #Request out to the server and pull for updates
        agent = pythonAgent(domain="127.0.0.1")
        text = agent.make_request()
        print(text) 
        #interval timer to be set before the next request