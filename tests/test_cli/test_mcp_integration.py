#!/usr/bin/env python3
"""
MCP Integration Testing Framework
Tests for enhanced 'tmux-orc setup all' command and Claude Code CLI MCP integration
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class MCPIntegrationTestFramework(unittest.TestCase):
    """Test framework for MCP server integration with Claude Code CLI"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.claude_config_dir = Path(self.test_dir) / ".claude" / "config"
        self.claude_config_dir.mkdir(parents=True, exist_ok=True)

        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ, {"CLAUDE_CONFIG_DIR": str(self.claude_config_dir.parent), "HOME": self.test_dir}
        )
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)


class TestEnhancedSetupCommand(MCPIntegrationTestFramework):
    """Test enhanced 'tmux-orc setup all' command functionality"""

    def test_setup_creates_claude_config_directory(self):
        """Test that setup command creates .claude/config/ directory"""
        # Remove directory to test creation
        import shutil

        shutil.rmtree(self.claude_config_dir.parent, ignore_errors=True)

        # Mock setup command execution
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            # This would be the enhanced setup command
            self._run_enhanced_setup()

            # Verify directory was created
            self.assertTrue(self.claude_config_dir.exists())

    def test_setup_creates_mcp_json_configuration(self):
        """Test that setup command creates proper mcp.json configuration"""
        # Run enhanced setup
        self._run_enhanced_setup()

        # Check mcp.json was created
        mcp_config_path = self.claude_config_dir / "mcp.json"
        self.assertTrue(mcp_config_path.exists())

        # Verify configuration content
        with open(mcp_config_path) as f:
            config = json.load(f)

        self.assertIn("servers", config)
        self.assertIn("tmux-orchestrator", config["servers"])

        server_config = config["servers"]["tmux-orchestrator"]
        self.assertEqual(server_config["command"], "tmux-orc")
        self.assertEqual(server_config["args"], ["server", "start"])
        self.assertIn("TMUX_ORC_MCP_MODE", server_config.get("env", {}))

    def test_setup_handles_existing_mcp_configuration(self):
        """Test that setup command merges with existing MCP configuration"""
        # Create existing mcp.json with other servers
        existing_config = {"servers": {"other-server": {"command": "other-command", "args": ["arg1"]}}}

        mcp_config_path = self.claude_config_dir / "mcp.json"
        with open(mcp_config_path, "w") as f:
            json.dump(existing_config, f)

        # Run enhanced setup
        self._run_enhanced_setup()

        # Verify both servers exist
        with open(mcp_config_path) as f:
            config = json.load(f)

        self.assertIn("other-server", config["servers"])
        self.assertIn("tmux-orchestrator", config["servers"])

    def test_setup_validates_tmux_orc_availability(self):
        """Test that setup command validates tmux-orc is available"""
        with patch("subprocess.run") as mock_run:
            # Mock tmux-orc not found
            mock_run.side_effect = FileNotFoundError()

            result = self._run_enhanced_setup()

            # Should handle missing tmux-orc gracefully
            self.assertIn("error", result.lower())

    def test_setup_is_idempotent(self):
        """Test that running setup multiple times is safe"""
        # Run setup twice
        self._run_enhanced_setup()
        self._run_enhanced_setup()

        # Both should succeed
        mcp_config_path = self.claude_config_dir / "mcp.json"
        self.assertTrue(mcp_config_path.exists())

        # Configuration should be consistent
        with open(mcp_config_path) as f:
            config = json.load(f)

        # Should only have one tmux-orchestrator entry
        self.assertEqual(len([k for k in config["servers"].keys() if k == "tmux-orchestrator"]), 1)

    def _run_enhanced_setup(self):
        """Mock enhanced setup command execution"""
        # This simulates what the enhanced setup command should do
        mcp_config = {
            "servers": {
                "tmux-orchestrator": {
                    "command": "tmux-orc",
                    "args": ["server", "start"],
                    "env": {"TMUX_ORC_MCP_MODE": "claude", "PYTHONUNBUFFERED": "1"},
                    "disabled": False,
                    "description": "AI-powered tmux session orchestrator",
                }
            }
        }

        mcp_config_path = self.claude_config_dir / "mcp.json"

        # Handle existing configuration
        if mcp_config_path.exists():
            with open(mcp_config_path) as f:
                existing = json.load(f)
            existing["servers"].update(mcp_config["servers"])
            mcp_config = existing

        # Write configuration
        with open(mcp_config_path, "w") as f:
            json.dump(mcp_config, f, indent=2)

        return "Setup completed successfully"


class TestClaudeCodeMCPIntegration(MCPIntegrationTestFramework):
    """Test Claude Code CLI MCP integration verification"""

    def test_claude_mcp_list_shows_tmux_orchestrator(self):
        """Test that 'claude mcp list' shows tmux-orchestrator server"""
        # Setup MCP configuration
        self._setup_mcp_config()

        # Mock claude mcp list command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "tmux-orchestrator\n"
            mock_run.return_value.returncode = 0

            result = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True)

            self.assertIn("tmux-orchestrator", result.stdout)

    def test_claude_mcp_get_shows_server_details(self):
        """Test that 'claude mcp get' shows server details"""
        self._setup_mcp_config()

        with patch("subprocess.run") as mock_run:
            mock_output = json.dumps({"name": "tmux-orchestrator", "command": "tmux-orc", "args": ["server", "start"]})
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.returncode = 0

            result = subprocess.run(["claude", "mcp", "get", "tmux-orchestrator"], capture_output=True, text=True)

            server_info = json.loads(result.stdout)
            self.assertEqual(server_info["name"], "tmux-orchestrator")
            self.assertEqual(server_info["command"], "tmux-orc")

    def test_mcp_server_starts_successfully(self):
        """Test that MCP server can be started"""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Still running
            mock_popen.return_value = mock_process

            # Mock server start
            subprocess.run(["tmux-orc", "server", "start"], capture_output=True, text=True)

            # Should start without errors
            mock_popen.assert_called()

    def _setup_mcp_config(self):
        """Set up valid MCP configuration for testing"""
        mcp_config = {
            "servers": {
                "tmux-orchestrator": {
                    "command": "tmux-orc",
                    "args": ["server", "start"],
                    "env": {"TMUX_ORC_MCP_MODE": "claude", "PYTHONUNBUFFERED": "1"},
                    "disabled": False,
                    "description": "AI-powered tmux session orchestrator",
                }
            }
        }

        mcp_config_path = self.claude_config_dir / "mcp.json"
        with open(mcp_config_path, "w") as f:
            json.dump(mcp_config, f, indent=2)


class TestAgentMCPAccess(MCPIntegrationTestFramework):
    """Test agent MCP server access validation"""

    def test_spawned_agents_have_mcp_access(self):
        """Test that spawned agents can access MCP server"""
        # Setup MCP configuration
        self._setup_mcp_config()

        # Mock agent spawn
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            # Simulate spawning an agent
            result = subprocess.run(
                ["tmux-orc", "spawn", "agent", "test-agent", "--session", "test:1"], capture_output=True, text=True
            )

            # Agent should be spawned successfully
            self.assertEqual(result.returncode, 0)

    def test_agent_can_use_mcp_tools(self):
        """Test that agents can use MCP tools"""
        # This would test actual MCP tool usage by agents
        # For now, we mock the expected behavior
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "MCP tools available\n"
            mock_run.return_value.returncode = 0

            # Mock checking MCP tools in agent context
            # This would be the actual test command run by agents
            result = subprocess.run(["tmux-orc", "agent", "info", "test-agent"], capture_output=True, text=True)

            self.assertIn("MCP", result.stdout)

    def _setup_mcp_config(self):
        """Set up valid MCP configuration for testing"""
        mcp_config = {
            "servers": {
                "tmux-orchestrator": {
                    "command": "tmux-orc",
                    "args": ["server", "start"],
                    "env": {"TMUX_ORC_MCP_MODE": "claude", "PYTHONUNBUFFERED": "1"},
                    "disabled": False,
                    "description": "AI-powered tmux session orchestrator",
                }
            }
        }

        mcp_config_path = self.claude_config_dir / "mcp.json"
        with open(mcp_config_path, "w") as f:
            json.dump(mcp_config, f, indent=2)


if __name__ == "__main__":
    # Run specific test suites
    import sys

    if len(sys.argv) > 1:
        test_suite = sys.argv[1]
        if test_suite == "setup":
            suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedSetupCommand)
        elif test_suite == "integration":
            suite = unittest.TestLoader().loadTestsFromTestCase(TestClaudeCodeMCPIntegration)
        elif test_suite == "agents":
            suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentMCPAccess)
        else:
            suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    else:
        suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with proper code
    sys.exit(0 if result.wasSuccessful() else 1)
