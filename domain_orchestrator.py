from flask_application import FlaskApplication
from wsgi_creator import WSGICreator 


class DomainOrchestrator(): 
    """ 
    Class that handles all of the functions required to generate a new 'domain' including: 
    - Generating a new flask app and corresponding index.html 
    - Generating a new wsgi server for said flask application 
    - Generating adding the routing to the nginx server 
    - Updating the nginx server config
    """

    def __init__(self):
        # A dictionary that stores all of the values of any corresponding application. So that on a new loading of the program it can be booted 
        pass

    #TODO: Have it such that the user just inputs an entire FQDN and we parse out the other components?? (We parse components for naming purposes)
    # AS what would I do in the isntance of a subdomain 1
    def create_domain(self, domain_name: str, top_level_domain: str):
        """
        Completes all the set up for a provided domain, including the flask application, WSGI server, 
        and adding routing to nginx     

        Args: 
            domain_name - The name of the domain (ex. google, twitch)
            top_level_domain - The top level domain (ex. .com, .tv)
        """          
        # Create the flask application corresponding to the domain 
        flask_application = FlaskApplication(domain_name)
        app = flask_application.get_app() 
        
        # Create a correspodning WSGI server in a new file 
        wsgi_server = WSGICreator(app)
        wsgi_server.run_server(port=8000)

        # Update the nginx,conf file as well in reference 


        # Copy the update over to the nginx file 
        pass 

    def remove_domain(self): 
        #Shut down the wsgi server that is actively running
        # Remove the flask application class 
        # Remove the class that is being generated 
        pass

    def _save_domains(): 
        # Saves the domain that
        pass 

    def _update_nginx(): 
        pass 
        """
        
        """ 

