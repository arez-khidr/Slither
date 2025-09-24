//go:build integration
// +build integration

package agent

import (
	_ "embed"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

// NOTE: All the below tests are called from the tests/ folder with pytests.
// As integration requires communication with the flask server
type AgentIntegrationTestSuite struct {
	suite.Suite
	agent  *Agent
	config *agentConfig
}

//go:embed agent_config_test.json
var integrationConfigFile []byte

func (suite *AgentIntegrationTestSuite) SetupTest() {
	var err error
	suite.agent, suite.config, err = ExtractAndCreateAgent(integrationConfigFile)
	if err != nil {
		suite.T().Fatalf("Failed to setup test: %v", err)
	}
}

func (suite *AgentIntegrationTestSuite) TestBeaconIn() {
	commands, err := beaconIn(suite.agent, suite.config)
	fmt.Printf("Commands Retrieved: %v", commands)
	assert.NoError(suite.T(), err, "beaconIn threw an error unexpectedly")
	// Validate the commands are true
	expectCommands := []string{"echo hello", "echo fart"}
	assert.Equal(suite.T(), expectCommands, commands, "expectedcommands do not match recieved commands")
}

// Required test to be able to run beforehand using the testing module that is native to go
func TestAgentIntegrationTestSuite(t *testing.T) {
	suite.Run(t, new(AgentIntegrationTestSuite))
}
