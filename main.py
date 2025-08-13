from domain_orchestrator import DomainOrchestrator

#TODO: Implement a basic argparser in the command line for now 

dorch = DomainOrchestrator()
dorch.create_domain('localhost', '.com')
