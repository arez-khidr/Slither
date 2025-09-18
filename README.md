# 🚧 **Project Under Construction** 🚧
⚠️ This project is currently a work in progress.
Most features are not yet implemented, but updates will come soon.

Stay tuned for development progress and new commits!

# Slither - Python Command & Control Framework

Slither is a Python-based Command & Control (C2) framework designed for cybersecurity research and adversary simulation. 
It features HTTP-based communication, domain management, and a terminal user interface for operator control.

Many of Slither's features are inspired by those seen in other C2 Frameworks, specifically Sliver (the name of this project is a play on Sliver's name). 
Slither is unique in its focus on modularity of generating realistic web application instances as fronts from C2 communication.  

**For educational and testing purposes only.**

## Current Limitations

Slither is still a work in progress. As a result there are a lot of features still yet to be implemented. 
For more detailed information on Slither, check out my blog at https://arezkhidr.com 

## Current Features

- **Multi-Mode Agents**: Beacon and long-polling communication modes
- **Domain Management**: Create, manage, and remove C2 domains dynamically
- **HTTP Obfuscation**: Uses various file extensions (.css, .js, .png, etc.) for traffic masquerading
- **Command Execution**: Remote command execution on target systems
- **Agent Modification**: Runtime agent configuration changes
- **TUI Interface**: Terminal-based operator console
- **Redis Integration**: Command queuing and session management using Redis streams and lists
- **WSGI Deployment**: Production-ready Flask deployment with Gunicorn

## Incoming Features

- **Multi-Domain Agent Support**: Enable agents to communicate with and send commands to multiple domains simultaneously
- **Individual Agent Management**: Enhanced capabilities for managing agents individually as they point to specific domains
- **Nonce-Based Authentication**: Server identification of legitimate agent requests using nonces, with realistic webpage fallbacks for non-agent traffic
- **Encrypted Communications**: End-to-end encryption between agents and servers for secure data transmission
- **HTTPS Implementation**: Full HTTPS support for all agent-server communications
- **Proxy Support**: Agent capability to handle network proxy configurations
- **Infrastructure Separation**: Decoupling of C2 client and server components 
- **Enhanced Process Management**: Migration from custom scripts to established libraries for process management

## Architecture

```
Agent → Nginx (Redirector) → Flask (C2 Server) ← TUI (Operator)
```

Current components run on a single system but are designed for future separation.

## Project Structure

```
pyWebC2/
├── agent/              # Agent implementation
│   ├── agent.py        # Main agent code
│   ├── agent_config.json
│   └── agent_html.py
├── tests/              # Test suite
├── wsgi/               # Generated WSGI server configurations
├── templates/          # Genereated static files for Flask Applications
├── nginx/              # Generated Nginx configurations
├── webC2/              # Virtual environment
├── flask_application.py
├── domain_orchestrator.py
├── wsgi_creator.py
├── nginx_controller.py
├── command.py
├── read.py
├── main.py             # Terminal interface (TUI)
└── README.md
```


## License

This project is licensed under the MIT License - see the LICENSE file for details.
