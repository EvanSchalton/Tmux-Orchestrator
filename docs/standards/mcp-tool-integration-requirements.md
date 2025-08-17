# MCP Tool Integration Quality Requirements

## Overview
This document establishes comprehensive quality requirements for MCP tool integration in the Tmux Orchestrator CLI reflection architecture. These requirements ensure that CLI commands automatically generate high-quality, reliable, and secure MCP tools for AI agent interaction.

## MCP Tool Generation Standards

### 1. Automatic Tool Generation Requirements
Every CLI command MUST be compatible with automatic MCP tool generation:

```python
# ✅ CORRECT: MCP-ready CLI command
@click.command()
@click.argument('target', metavar='SESSION:WINDOW')
@click.option('--extend', help='Additional context to add')
@click.option('--json', is_flag=True, help='Output in JSON format')
def spawn_agent(target: str, extend: str, json: bool):
    """
    Spawn a new agent in the specified session.

    Creates a new AI agent in the target tmux session with the
    specified role and configuration.

    Examples:
        tmux-orc spawn agent dev-session:1 --extend "Python expert"
        tmux-orc spawn agent backend:2 --json

    Args:
        target: Target session in format session:window
        extend: Additional context for agent briefing
        json: Return structured JSON response
    """
    # Implementation...
```

### 2. CLI Command Documentation Standards
For optimal MCP tool generation, CLI commands MUST include:

#### Help Text Requirements
```python
def command_with_proper_help():
    """
    Primary description (becomes MCP tool description).

    Detailed explanation of what the command does and when to use it.
    This section provides context for AI agents to understand the tool's purpose.

    Examples:
        # Basic usage example
        tmux-orc command basic-arg

        # Advanced usage with options
        tmux-orc command advanced-arg --option value

        # Real-world scenario showing context
        tmux-orc command production-session:1 --mode production

    Args:
        arg1: Clear description with expected format and constraints
        arg2: Description including valid values, ranges, or patterns

    Returns:
        Description of what the command outputs or accomplishes

    Notes:
        Important warnings, prerequisites, or side effects
    """
```

#### Parameter Documentation
```python
# ✅ CORRECT: Well-documented parameters
@click.argument('session', metavar='SESSION:WINDOW',
                help='Target session in format session:window')
@click.option('--role',
              type=click.Choice(['developer', 'qa', 'devops']),
              help='Agent role determining capabilities and context')
@click.option('--timeout', type=int, default=30,
              help='Operation timeout in seconds (default: 30)')

# ❌ INCORRECT: Undocumented parameters
@click.argument('session')
@click.option('--role')
@click.option('--timeout', type=int)
```

### 3. JSON Output Compatibility
All commands exposed as MCP tools MUST support JSON output:

```python
def mcp_compatible_command():
    """Command compatible with MCP tool generation."""
    try:
        result = perform_operation()

        if json_flag:
            response = {
                "success": True,
                "data": result,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "command": "command-name",
                "execution_time": execution_time,
                "version": "1.0"
            }
            click.echo(json.dumps(response, indent=2))
        else:
            display_formatted_result(result)

    except Exception as e:
        if json_flag:
            error_response = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "command": "command-name"
            }
            click.echo(json.dumps(error_response, indent=2))
        else:
            handle_error_display(e)
```

## MCP Server Quality Standards

### 1. CLI Reflection Implementation
```python
class QualityMCPServer:
    """High-quality MCP server with comprehensive CLI reflection."""

    async def discover_cli_structure(self) -> Dict[str, Any]:
        """
        Discover CLI structure with comprehensive error handling.

        Returns:
            Complete CLI structure or empty dict on failure
        """
        try:
            # Execute CLI reflection with timeout and validation
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            # Validate result
            if result.returncode != 0:
                logger.error(f"CLI reflection failed: {result.stderr}")
                return {}

            # Parse and validate JSON
            cli_structure = json.loads(result.stdout)

            # Validate structure format
            if not isinstance(cli_structure, dict):
                logger.error("CLI reflection returned invalid format")
                return {}

            # Log discovery results
            commands = self._extract_commands(cli_structure)
            logger.info(f"Discovered {len(commands)} CLI commands")

            return cli_structure

        except subprocess.TimeoutExpired:
            logger.error("CLI reflection timed out")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CLI reflection JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"CLI discovery failed: {e}")
            return {}

    def _extract_commands(self, cli_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate command information."""
        commands = {}

        for key, value in cli_structure.items():
            if isinstance(value, dict) and value.get('type') == 'command':
                # Validate command structure
                if self._validate_command_structure(key, value):
                    commands[key] = value
                else:
                    logger.warning(f"Skipping invalid command: {key}")

        return commands

    def _validate_command_structure(self, name: str, command_info: Dict[str, Any]) -> bool:
        """Validate command structure for MCP compatibility."""
        required_fields = ['type']

        for field in required_fields:
            if field not in command_info:
                logger.warning(f"Command {name} missing required field: {field}")
                return False

        return True
```

### 2. Tool Generation Quality Control
```python
def generate_high_quality_mcp_tool(self, command_name: str, command_info: Dict[str, Any]) -> None:
    """Generate high-quality MCP tool with comprehensive validation."""

    # Validate command eligibility
    if not self._is_command_mcp_eligible(command_name, command_info):
        logger.info(f"Skipping command {command_name}: not eligible for MCP")
        return

    # Clean tool name
    tool_name = self._clean_tool_name(command_name)

    # Extract and validate description
    description = self._extract_description(command_info)
    if not description:
        logger.warning(f"Command {command_name} has no description")
        description = f"Execute tmux-orc {command_name}"

    # Create tool function with comprehensive error handling
    tool_function = self._create_robust_tool_function(command_name, command_info)

    # Register tool with FastMCP
    try:
        decorated_tool = self.mcp.tool(
            name=tool_name,
            description=self._truncate_description(description)
        )(tool_function)

        # Store tool metadata
        self.generated_tools[tool_name] = {
            "command_name": command_name,
            "description": description,
            "function": decorated_tool,
            "generated_at": datetime.utcnow().isoformat(),
            "quality_score": self._calculate_quality_score(command_info)
        }

        logger.debug(f"Generated high-quality MCP tool: {tool_name}")

    except Exception as e:
        logger.error(f"Failed to register tool {tool_name}: {e}")

def _is_command_mcp_eligible(self, command_name: str, command_info: Dict[str, Any]) -> bool:
    """Determine if command should be exposed as MCP tool."""

    # Security check - restricted commands
    restricted_commands = {
        'daemon',      # Internal daemon management
        'debug',       # Debug commands may expose sensitive info
        'raw-execute', # Direct execution without validation
        'setup-dev',   # Development setup commands
    }

    if command_name in restricted_commands:
        return False

    # Quality check - must have reasonable help text
    help_text = command_info.get('help', '') or command_info.get('short_help', '')
    if not help_text or len(help_text.strip()) < 10:
        logger.warning(f"Command {command_name} has insufficient help text")
        return False

    return True

def _calculate_quality_score(self, command_info: Dict[str, Any]) -> float:
    """Calculate quality score for MCP tool."""
    score = 0.0

    # Documentation quality (40% of score)
    help_text = command_info.get('help', '')
    if help_text:
        if len(help_text) > 100:
            score += 0.2
        if 'Examples:' in help_text:
            score += 0.1
        if 'Args:' in help_text:
            score += 0.1

    # Parameter quality (30% of score)
    params = command_info.get('params', [])
    if params:
        documented_params = sum(1 for p in params if p.get('help'))
        score += 0.3 * (documented_params / len(params))

    # JSON support (20% of score)
    if self._command_supports_json(command_info.get('name', '')):
        score += 0.2

    # Error handling (10% of score)
    if command_info.get('error_handling', False):
        score += 0.1

    return min(score, 1.0)
```

### 3. Error Handling and Resilience
```python
async def robust_cli_execution(self, command_name: str, cli_args: List[str]) -> Dict[str, Any]:
    """Execute CLI command with comprehensive error handling."""
    start_time = time.time()

    try:
        # Validate arguments
        self._validate_cli_arguments(cli_args)

        # Build command with security validation
        cmd_parts = ["tmux-orc", command_name] + cli_args

        # Add JSON flag if supported and not present
        if "--json" not in cli_args and self._command_supports_json(command_name):
            cmd_parts.append("--json")

        # Execute with resource limits
        result = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_safe_environment()
            ),
            timeout=60.0
        )

        stdout, stderr = await result.communicate()
        execution_time = time.time() - start_time

        # Parse output
        parsed_output = self._parse_command_output(stdout.decode())

        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "execution_time": execution_time,
            "parsed_output": parsed_output,
            "command_line": " ".join(cmd_parts),
            "mcp_version": "1.0"
        }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Command execution timed out",
            "error_type": "TimeoutError",
            "execution_time": time.time() - start_time,
            "command_line": " ".join(["tmux-orc", command_name] + cli_args)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "execution_time": time.time() - start_time,
            "command_line": " ".join(["tmux-orc", command_name] + cli_args)
        }
```

## Integration Testing Requirements

### 1. MCP Tool Testing Framework
```python
import pytest
from fastmcp.testing import MCPTestClient

class TestMCPIntegration:
    """Comprehensive MCP tool integration tests."""

    @pytest.fixture
    async def mcp_client(self):
        """Create MCP test client."""
        server = FreshCLIToMCPServer("test-server")
        await server.discover_cli_structure()
        server.generate_all_mcp_tools()

        client = MCPTestClient(server.mcp)
        await client.connect()
        return client

    async def test_all_tools_generated(self, mcp_client):
        """Test that all eligible CLI commands become MCP tools."""
        # Get CLI structure
        result = subprocess.run(
            ["tmux-orc", "reflect", "--format", "json"],
            capture_output=True, text=True
        )
        cli_structure = json.loads(result.stdout)

        # Get available MCP tools
        tools = await mcp_client.list_tools()
        tool_names = {tool.name for tool in tools}

        # Check that eligible commands have tools
        eligible_commands = self._get_eligible_commands(cli_structure)
        for command in eligible_commands:
            tool_name = command.replace("-", "_")
            assert tool_name in tool_names, f"Missing MCP tool for command: {command}"

    async def test_tool_execution_quality(self, mcp_client):
        """Test quality of MCP tool execution."""
        tools = await mcp_client.list_tools()

        for tool in tools[:5]:  # Test first 5 tools
            # Test with valid arguments
            result = await mcp_client.call_tool(tool.name, {})

            # Validate response structure
            assert isinstance(result, dict)
            assert "success" in result
            assert "command" in result

            # Test error handling
            invalid_result = await mcp_client.call_tool(
                tool.name, {"invalid_arg": "invalid_value"}
            )
            assert isinstance(invalid_result, dict)
            assert "success" in invalid_result

    async def test_json_output_consistency(self, mcp_client):
        """Test JSON output consistency between CLI and MCP."""
        test_commands = ["list", "status", "reflect"]

        for command in test_commands:
            # Execute via CLI
            cli_result = subprocess.run(
                ["tmux-orc", command, "--json"],
                capture_output=True, text=True
            )

            if cli_result.returncode == 0:
                cli_output = json.loads(cli_result.stdout)

                # Execute via MCP
                tool_name = command.replace("-", "_")
                mcp_result = await mcp_client.call_tool(tool_name, {})

                # Compare outputs (structure should be similar)
                assert mcp_result["success"] == True
                assert "data" in mcp_result or "result" in mcp_result
```

### 2. Performance Testing
```python
class TestMCPPerformance:
    """Performance testing for MCP tools."""

    async def test_tool_response_time(self, mcp_client):
        """Test MCP tool response times."""
        tools = await mcp_client.list_tools()

        for tool in tools:
            start_time = time.time()
            result = await mcp_client.call_tool(tool.name, {})
            execution_time = time.time() - start_time

            # MCP tools should respond within 5 seconds
            assert execution_time < 5.0, f"Tool {tool.name} too slow: {execution_time:.2f}s"

    async def test_concurrent_tool_execution(self, mcp_client):
        """Test concurrent MCP tool execution."""
        tools = await mcp_client.list_tools()

        # Execute multiple tools concurrently
        tasks = []
        for tool in tools[:3]:
            task = mcp_client.call_tool(tool.name, {})
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Tool {tools[i].name} failed: {result}"
```

## Quality Metrics and Monitoring

### 1. MCP Tool Quality Metrics
```python
class MCPQualityMetrics:
    """Track and report MCP tool quality metrics."""

    def __init__(self):
        self.metrics = {
            "total_tools": 0,
            "high_quality_tools": 0,
            "json_compatible_tools": 0,
            "documented_tools": 0,
            "error_rate": 0.0,
            "average_response_time": 0.0
        }

    def calculate_tool_quality_score(self, tool_metadata: Dict[str, Any]) -> float:
        """Calculate overall quality score for a tool."""
        scores = []

        # Documentation score
        if tool_metadata.get("description"):
            desc_len = len(tool_metadata["description"])
            doc_score = min(desc_len / 200, 1.0)  # Target 200+ chars
            scores.append(doc_score * 0.3)

        # JSON compatibility score
        if tool_metadata.get("json_compatible", False):
            scores.append(0.2)

        # Error handling score
        if tool_metadata.get("error_handling", False):
            scores.append(0.2)

        # Performance score
        response_time = tool_metadata.get("avg_response_time", 0)
        if response_time > 0:
            perf_score = max(0, 1.0 - (response_time / 5.0))  # Target <5s
            scores.append(perf_score * 0.3)

        return sum(scores)

    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        total_score = sum(
            self.calculate_tool_quality_score(tool)
            for tool in self.generated_tools.values()
        )

        return {
            "overall_quality": total_score / len(self.generated_tools) if self.generated_tools else 0,
            "metrics": self.metrics,
            "recommendations": self._generate_recommendations(),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []

        if self.metrics["documented_tools"] / self.metrics["total_tools"] < 0.8:
            recommendations.append("Improve CLI command documentation")

        if self.metrics["json_compatible_tools"] / self.metrics["total_tools"] < 0.9:
            recommendations.append("Add JSON output support to more commands")

        if self.metrics["error_rate"] > 0.1:
            recommendations.append("Improve error handling in CLI commands")

        if self.metrics["average_response_time"] > 3.0:
            recommendations.append("Optimize CLI command performance")

        return recommendations
```

### 2. Continuous Quality Monitoring
```python
class MCPQualityMonitor:
    """Continuous monitoring of MCP tool quality."""

    def __init__(self):
        self.quality_history = []
        self.alert_thresholds = {
            "min_quality_score": 0.7,
            "max_error_rate": 0.05,
            "max_response_time": 5.0
        }

    async def run_quality_checks(self) -> Dict[str, Any]:
        """Run comprehensive quality checks."""
        start_time = time.time()

        # Discover current CLI structure
        cli_structure = await self.discover_cli_structure()

        # Generate quality metrics
        metrics = self._calculate_quality_metrics(cli_structure)

        # Check against thresholds
        alerts = self._check_quality_thresholds(metrics)

        # Store results
        quality_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "alerts": alerts,
            "check_duration": time.time() - start_time
        }

        self.quality_history.append(quality_report)

        return quality_report

    def _check_quality_thresholds(self, metrics: Dict[str, Any]) -> List[str]:
        """Check metrics against quality thresholds."""
        alerts = []

        if metrics.get("overall_quality", 0) < self.alert_thresholds["min_quality_score"]:
            alerts.append("Overall quality score below threshold")

        if metrics.get("error_rate", 0) > self.alert_thresholds["max_error_rate"]:
            alerts.append("Error rate above threshold")

        if metrics.get("avg_response_time", 0) > self.alert_thresholds["max_response_time"]:
            alerts.append("Average response time above threshold")

        return alerts
```

## Deployment and Configuration Standards

### 1. MCP Server Deployment Configuration
```python
# Production MCP server configuration
MCP_SERVER_CONFIG = {
    "server_name": "tmux-orchestrator-production",
    "quality_monitoring": True,
    "performance_logging": True,
    "error_tracking": True,
    "tool_validation": True,
    "security_scanning": True,
    "rate_limiting": {
        "max_requests_per_minute": 60,
        "max_concurrent_requests": 10
    },
    "timeouts": {
        "cli_discovery": 30,
        "tool_execution": 60,
        "server_startup": 120
    },
    "logging": {
        "level": "INFO",
        "format": "json",
        "file": "/var/log/tmux-orc-mcp.log"
    }
}
```

### 2. Quality Assurance Pipeline
```yaml
# .github/workflows/mcp-quality-check.yml
name: MCP Tool Quality Check

on: [push, pull_request]

jobs:
  mcp-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio

      - name: Test CLI reflection
        run: |
          tmux-orc reflect --format json > cli-structure.json
          python scripts/validate-cli-structure.py cli-structure.json

      - name: Test MCP tool generation
        run: |
          python -m pytest tests/test_mcp_quality.py -v

      - name: Generate quality report
        run: |
          python scripts/generate-mcp-quality-report.py

      - name: Upload quality artifacts
        uses: actions/upload-artifact@v3
        with:
          name: mcp-quality-report
          path: |
            cli-structure.json
            mcp-quality-report.json
```

## Documentation Requirements

### 1. MCP Integration Documentation
Each CLI command that generates an MCP tool MUST include:
- Clear purpose and use cases
- Parameter descriptions with types and constraints
- Example usage scenarios
- Error conditions and handling
- Performance characteristics
- Security considerations

### 2. Quality Assurance Documentation
```markdown
# MCP Tool Quality Checklist

## Pre-Release Checklist
- [ ] All CLI commands have comprehensive help text
- [ ] JSON output format is standardized
- [ ] Error handling is consistent
- [ ] Security validation is implemented
- [ ] Performance meets requirements (<5s response time)
- [ ] Documentation is complete and accurate

## Post-Release Monitoring
- [ ] Quality metrics are being tracked
- [ ] Error rates are within acceptable limits
- [ ] Performance meets SLA requirements
- [ ] User feedback is positive
- [ ] Integration tests are passing
```

This comprehensive framework ensures that the CLI reflection architecture generates high-quality, reliable, and maintainable MCP tools that provide excellent integration capabilities for AI agents.
