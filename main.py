import cmd
from domain_orchestrator import DomainOrchestrator

class PyWebC2Shell(cmd.Cmd):
    intro = 'Welcome to pyWebC2 Interactive Shell. Type help or ? to list commands.\n'
    prompt = 'pyWebC2> '
    
    def __init__(self):
        super().__init__()
        self.dorch = DomainOrchestrator()
    
    def do_create(self, line):
        """Create a new domain: create <domain_name> [port]"""
        args = line.split()
        if not args:
            print("Usage: create <domain_name> [port]")
            return
        
        domain_name = args[0]
        port = int(args[1]) if len(args) > 1 else None
        self.dorch.create_domain(domain_name, '.com', port)
    
    def do_remove(self, line):
        """Remove a domain: remove <domain_name>"""
        if not line.strip():
            print("Usage: remove <domain_name>")
            return
        
        self.dorch.remove_domain(line.strip())
    
    def do_list(self, line):
        """List all active domains"""
        print("Active domains:", self.dorch.domainDictionary)
    
    def do_pause(self, line):
        """Pause a running domain: pause <domain_name>"""
        if not line.strip():
            print("Usage: pause <domain_name>")
            return
        
        self.dorch.pause_domain(line.strip())
    
    def do_resume(self, line):
        """Resume a paused domain: resume <domain_name>"""
        if not line.strip():
            print("Usage: resume <domain_name>")
            return
        
        self.dorch.resume_domain(line.strip())
    
    def do_exit(self, line):
        """Exit the shell"""
        return True
    
    def do_quit(self, line):
        """Exit the shell"""
        return True

def main():
    PyWebC2Shell().cmdloop()

if __name__ == "__main__":
    main()