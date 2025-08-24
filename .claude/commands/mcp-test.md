# MCP Comprehensive Test Command

**Command:** `mcp-comprehensive-test`
**Purpose:** Systematically test ALL MCP commands against CLI equivalents for complete parity validation
**Usage:** Reference this command to trigger comprehensive MCP server testing and issue resolution

## Procedure

### Phase 1: Discovery & Setup
1. **Get CLI Structure**
   ```bash
   tmux-orc reflect --format json
   ```
   - Extract ALL commands from the reflection
   - Build complete test matrix of MCP vs CLI commands

2. **Initialize Test Environment**
   - Create TodoWrite task list for tracking
   - Establish baseline test session if needed
   - Document test start time and environment

### Phase 2: Systematic MCP Testing

#### Test Execution Strategy - Intentional Sequencing

**IMPORTANT**: Tests must be executed in a specific sequence to create realistic scenarios and validate actual functionality, not just command syntax.

#### Test Sequence Flow:

1. **Initial System State**
   - `mcp__tmux-orchestrator__list` - Verify empty system
   - `mcp__tmux-orchestrator__status` - Check clean status
   - `mcp__tmux-orchestrator__monitor action=status` - Ensure daemon not running
   - `mcp__tmux-orchestrator__agent action=list` - Confirm no agents

2. **Setup & Configuration**
   - `mcp__tmux-orchestrator__setup action=check` - Verify requirements
   - `mcp__tmux-orchestrator__context action=list` - List available contexts
   - `mcp__tmux-orchestrator__context action=show args=[orc]` - Load orchestrator context
   - `mcp__tmux-orchestrator__context action=show args=[pm]` - Load PM context

3. **Daemon & Monitoring Setup**
   - `mcp__tmux-orchestrator__monitor action=start` - Start monitoring daemon
   - `mcp__tmux-orchestrator__monitor action=status` - Verify daemon running
   - `mcp__tmux-orchestrator__daemon action=status` - Check daemon health
   - `mcp__tmux-orchestrator__monitor action=logs` - View initial logs

4. **Agent Spawning & Management**
   - `mcp__tmux-orchestrator__spawn action=pm args=[--session, test-mcp:0]` - Spawn PM
   - `mcp__tmux-orchestrator__list` - Verify PM appears in list
   - `mcp__tmux-orchestrator__agent action=status` - Check PM status
   - `mcp__tmux-orchestrator__spawn action=agent args=[developer, test-mcp:1]` - Spawn developer
   - `mcp__tmux-orchestrator__spawn action=agent args=[qa, test-mcp:2]` - Spawn QA
   - `mcp__tmux-orchestrator__list` - Verify all agents listed

5. **Communication Testing (with live agents)**
   - `mcp__tmux-orchestrator__agent action=send target=test-mcp:0 args=["Hello PM, please confirm receipt"]`
   - `mcp__tmux-orchestrator__agent action=send target=test-mcp:1 args=["Developer, implement feature X"]`
   - `mcp__tmux-orchestrator__pm action=broadcast args=["Team meeting in 5 minutes"]`
   - `mcp__tmux-orchestrator__team action=broadcast args=["System maintenance alert"]`
   - `mcp__tmux-orchestrator__pubsub action=publish args=["Test notification"]`

6. **Team Coordination (with active team)**
   - `mcp__tmux-orchestrator__team action=status args=[test-mcp]`
   - `mcp__tmux-orchestrator__team action=list`
   - `mcp__tmux-orchestrator__orchestrator action=list`
   - `mcp__tmux-orchestrator__orchestrator action=status`

7. **Agent Health & Recovery**
   - `mcp__tmux-orchestrator__agent action=info target=test-mcp:1`
   - `mcp__tmux-orchestrator__agent action=restart target=test-mcp:2`
   - `mcp__tmux-orchestrator__recovery action=status`
   - `mcp__tmux-orchestrator__monitor action=recovery-status`

8. **Task Management (with active agents)**
   - `mcp__tmux-orchestrator__tasks action=create args=["Implement login feature"]`
   - `mcp__tmux-orchestrator__tasks action=list`
   - `mcp__tmux-orchestrator__tasks action=distribute`
   - `mcp__tmux-orchestrator__tasks action=status`

9. **Session Management**
   - `mcp__tmux-orchestrator__session action=list`
   - `mcp__tmux-orchestrator__session action=attach target=test-mcp:1` (test, then detach)

10. **Cleanup & Teardown**
    - `mcp__tmux-orchestrator__agent action=kill target=test-mcp:2` - Kill QA agent
    - `mcp__tmux-orchestrator__list` - Verify agent removed
    - `mcp__tmux-orchestrator__agent action=kill target=test-mcp:1` - Kill developer
    - `mcp__tmux-orchestrator__orchestrator action=kill args=[test-mcp]` - Kill PM
    - `mcp__tmux-orchestrator__orchestrator action=kill-all` - Ensure all killed
    - `mcp__tmux-orchestrator__monitor action=stop` - Stop daemon
    - `mcp__tmux-orchestrator__list` - Verify empty system

#### Complete Command Coverage (ALL commands from reflect):

1. **Core System Commands**
   - `mcp__tmux-orchestrator__list` vs `tmux-orc list`
   - `mcp__tmux-orchestrator__status` vs `tmux-orc status`
   - `mcp__tmux-orchestrator__reflect` vs `tmux-orc reflect`
   - `mcp__tmux-orchestrator__quick_deploy args=[frontend, 3]` vs `tmux-orc quick-deploy frontend 3`
   - `mcp__tmux-orchestrator__execute args=[./prd.md]` vs `tmux-orc execute ./prd.md`

2. **Agent Management (Complete)**
   - `mcp__tmux-orchestrator__agent action=deploy args=[frontend, developer]` vs `tmux-orc agent deploy frontend developer`
   - `mcp__tmux-orchestrator__agent action=message target=session:window args=["test"]` vs `tmux-orc agent message session:window "test"`
   - `mcp__tmux-orchestrator__agent action=send target=session:window args=["test"]` vs `tmux-orc agent send session:window "test"`
   - `mcp__tmux-orchestrator__agent action=attach target=session:window` vs `tmux-orc agent attach session:window`
   - `mcp__tmux-orchestrator__agent action=restart target=session:window` vs `tmux-orc agent restart session:window`
   - `mcp__tmux-orchestrator__agent action=status` vs `tmux-orc agent status`
   - `mcp__tmux-orchestrator__agent action=kill target=session:window` vs `tmux-orc agent kill session:window`
   - `mcp__tmux-orchestrator__agent action=info target=session:window` vs `tmux-orc agent info session:window`
   - `mcp__tmux-orchestrator__agent action=list` vs `tmux-orc agent list`
   - `mcp__tmux-orchestrator__agent action=kill-all` vs `tmux-orc agent kill-all`

3. **Monitor Operations (Complete)**
   - `mcp__tmux-orchestrator__monitor action=start` vs `tmux-orc monitor start`
   - `mcp__tmux-orchestrator__monitor action=stop` vs `tmux-orc monitor stop`
   - `mcp__tmux-orchestrator__monitor action=logs` vs `tmux-orc monitor logs`
   - `mcp__tmux-orchestrator__monitor action=status` vs `tmux-orc monitor status`
   - `mcp__tmux-orchestrator__monitor action=recovery-start` vs `tmux-orc monitor recovery-start`
   - `mcp__tmux-orchestrator__monitor action=recovery-stop` vs `tmux-orc monitor recovery-stop`
   - `mcp__tmux-orchestrator__monitor action=recovery-status` vs `tmux-orc monitor recovery-status`
   - `mcp__tmux-orchestrator__monitor action=recovery-logs` vs `tmux-orc monitor recovery-logs`
   - `mcp__tmux-orchestrator__monitor action=dashboard` vs `tmux-orc monitor dashboard`
   - `mcp__tmux-orchestrator__monitor action=performance` vs `tmux-orc monitor performance`

4. **PM Operations (Complete)**
   - `mcp__tmux-orchestrator__pm action=checkin` vs `tmux-orc pm checkin`
   - `mcp__tmux-orchestrator__pm action=message args=["message"]` vs `tmux-orc pm message "message"`
   - `mcp__tmux-orchestrator__pm action=broadcast args=["message"]` vs `tmux-orc pm broadcast "message"`
   - `mcp__tmux-orchestrator__pm action=custom-checkin args=["custom"]` vs `tmux-orc pm custom-checkin "custom"`
   - `mcp__tmux-orchestrator__pm action=status` vs `tmux-orc pm status`
   - `mcp__tmux-orchestrator__pm action=create args=[project-name]` vs `tmux-orc pm create project-name`

5. **Context Operations (Complete)**
   - `mcp__tmux-orchestrator__context action=show args=[orc]` vs `tmux-orc context show orc`
   - `mcp__tmux-orchestrator__context action=show args=[orc]` vs `tmux-orc context show orc` (orchestrator context)
   - `mcp__tmux-orchestrator__context action=show args=[pm]` vs `tmux-orc context show pm`
   - `mcp__tmux-orchestrator__context action=show args=[mcp]` vs `tmux-orc context show mcp`
   - `mcp__tmux-orchestrator__context action=show args=[cleanup]` vs `tmux-orc context show cleanup`
   - `mcp__tmux-orchestrator__context action=show args=[tmux-comms]` vs `tmux-orc context show tmux-comms`
   - `mcp__tmux-orchestrator__context action=show args=[integration-test]` vs `tmux-orc context show integration-test`
   - `mcp__tmux-orchestrator__context action=list` vs `tmux-orc context list`
   - `mcp__tmux-orchestrator__context action=spawn args=[role, session:window]` vs `tmux-orc context spawn role session:window`
   - `mcp__tmux-orchestrator__context action=export args=[role]` vs `tmux-orc context export role`

6. **Team Coordination (Complete)**
   - `mcp__tmux-orchestrator__team action=status args=[session]` vs `tmux-orc team status session`
   - `mcp__tmux-orchestrator__team action=list` vs `tmux-orc team list`
   - `mcp__tmux-orchestrator__team action=broadcast args=["message"]` vs `tmux-orc team broadcast "message"`
   - `mcp__tmux-orchestrator__team action=deploy args=[frontend, 3]` vs `tmux-orc team deploy frontend 3`
   - `mcp__tmux-orchestrator__team action=recover args=[session]` vs `tmux-orc team recover session`

7. **Orchestrator Management (Complete)**
   - `mcp__tmux-orchestrator__orchestrator action=start` vs `tmux-orc orchestrator start`
   - `mcp__tmux-orchestrator__orchestrator action=schedule args=[cron-spec]` vs `tmux-orc orchestrator schedule "cron-spec"`
   - `mcp__tmux-orchestrator__orchestrator action=status` vs `tmux-orc orchestrator status`
   - `mcp__tmux-orchestrator__orchestrator action=list` vs `tmux-orc orchestrator list`
   - `mcp__tmux-orchestrator__orchestrator action=kill args=[session]` vs `tmux-orc orchestrator kill session`
   - `mcp__tmux-orchestrator__orchestrator action=kill-all` vs `tmux-orc orchestrator kill-all`
   - `mcp__tmux-orchestrator__orchestrator action=broadcast args=["message"]` vs `tmux-orc orchestrator broadcast "message"`

8. **Setup Operations (Complete)**
   - `mcp__tmux-orchestrator__setup action=mcp` vs `tmux-orc setup mcp`
   - `mcp__tmux-orchestrator__setup action=check-requirements` vs `tmux-orc setup check-requirements`
   - `mcp__tmux-orchestrator__setup action=claude-code` vs `tmux-orc setup claude-code`
   - `mcp__tmux-orchestrator__setup action=vscode` vs `tmux-orc setup vscode`
   - `mcp__tmux-orchestrator__setup action=tmux` vs `tmux-orc setup tmux`
   - `mcp__tmux-orchestrator__setup action=all` vs `tmux-orc setup all`
   - `mcp__tmux-orchestrator__setup action=check` vs `tmux-orc setup check`

9. **Spawn Operations (Complete)**
   - `mcp__tmux-orchestrator__spawn action=orc args=[--session, session:window]` vs `tmux-orc spawn orc --session session:window`
   - `mcp__tmux-orchestrator__spawn action=pm args=[--session, session:window]` vs `tmux-orc spawn pm --session session:window`
   - `mcp__tmux-orchestrator__spawn action=agent args=[developer, session:window]` vs `tmux-orc spawn agent developer session:window`

10. **Recovery System (Complete)**
    - `mcp__tmux-orchestrator__recovery action=start` vs `tmux-orc recovery start`
    - `mcp__tmux-orchestrator__recovery action=stop` vs `tmux-orc recovery stop`
    - `mcp__tmux-orchestrator__recovery action=status` vs `tmux-orc recovery status`
    - `mcp__tmux-orchestrator__recovery action=test` vs `tmux-orc recovery test`

11. **Session Management (Complete)**
    - `mcp__tmux-orchestrator__session action=list` vs `tmux-orc session list`
    - `mcp__tmux-orchestrator__session action=attach target=session:window` vs `tmux-orc session attach session:window`

12. **PubSub Operations (Complete)**
    - `mcp__tmux-orchestrator__pubsub action=publish args=["message"]` vs `tmux-orc pubsub publish "message"`
    - `mcp__tmux-orchestrator__pubsub action=read` vs `tmux-orc pubsub read`
    - `mcp__tmux-orchestrator__pubsub action=status` vs `tmux-orc pubsub status`
    - `mcp__tmux-orchestrator__pubsub action=stats` vs `tmux-orc pubsub stats`
    - `mcp__tmux-orchestrator__pubsub action=query args=[pattern]` vs `tmux-orc pubsub query pattern`

13. **Daemon Management (Complete)**
    - `mcp__tmux-orchestrator__daemon action=start` vs `tmux-orc daemon start`
    - `mcp__tmux-orchestrator__daemon action=stop` vs `tmux-orc daemon stop`
    - `mcp__tmux-orchestrator__daemon action=status` vs `tmux-orc daemon status`
    - `mcp__tmux-orchestrator__daemon action=restart` vs `tmux-orc daemon restart`
    - `mcp__tmux-orchestrator__daemon action=logs` vs `tmux-orc daemon logs`

14. **Task Management (Complete)**
    - `mcp__tmux-orchestrator__tasks action=create args=[task-name]` vs `tmux-orc tasks create task-name`
    - `mcp__tmux-orchestrator__tasks action=status` vs `tmux-orc tasks status`
    - `mcp__tmux-orchestrator__tasks action=distribute` vs `tmux-orc tasks distribute`
    - `mcp__tmux-orchestrator__tasks action=export` vs `tmux-orc tasks export`
    - `mcp__tmux-orchestrator__tasks action=archive args=[project]` vs `tmux-orc tasks archive project`
    - `mcp__tmux-orchestrator__tasks action=list` vs `tmux-orc tasks list`
    - `mcp__tmux-orchestrator__tasks action=generate args=[from-file]` vs `tmux-orc tasks generate from-file`

15. **Error Management (Complete)**
    - `mcp__tmux-orchestrator__errors action=summary` vs `tmux-orc errors summary`
    - `mcp__tmux-orchestrator__errors action=recent` vs `tmux-orc errors recent`
    - `mcp__tmux-orchestrator__errors action=clear` vs `tmux-orc errors clear`
    - `mcp__tmux-orchestrator__errors action=stats` vs `tmux-orc errors stats`

16. **Server Operations (Complete)**
    - `mcp__tmux-orchestrator__server action=start` vs `tmux-orc server start`
    - `mcp__tmux-orchestrator__server action=status` vs `tmux-orc server status`
    - `mcp__tmux-orchestrator__server action=tools` vs `tmux-orc server tools`
    - `mcp__tmux-orchestrator__server action=setup` vs `tmux-orc server setup`
    - `mcp__tmux-orchestrator__server action=toggle` vs `tmux-orc server toggle`

### Phase 3: Results Analysis

#### Success Criteria Evaluation:
- **Perfect Match:** MCP output identical to CLI output
- **Functional Match:** MCP achieves same result with acceptable formatting differences
- **Parameter Issue:** MCP works but needs syntax refinement
- **Failure:** MCP returns empty/error results while CLI works

#### Classification Patterns:
- **Hierarchical Commands:** `mcp__tmux-orchestrator__[group] action=[action]`
- **Direct Commands:** `mcp__tmux-orchestrator__[command]`
- **Parameter Patterns:** `args=[]`, `target=`, `options={}`

#### Document Findings:
```markdown
# MCP Test Results - [ISO-TIMESTAMP]

## Executive Summary
- Success Rate: X/Y (Z%)
- Failed Commands: [list]
- Root Cause Pattern: [analysis]

## Detailed Results
[Test matrix with status for each command]

## Technical Analysis
[Pattern analysis and root cause investigation]
```

### Phase 4: Issue Resolution

#### If Issues Found:
1. **Create Planning Directory**
   ```
   .tmux_orchestrator/planning/[ISO-TIMESTAMP]-mcp-reliability-fixes/
   ```

2. **Create Comprehensive Briefing**
   - Write detailed `briefing.md` with issue analysis
   - Include root cause investigation
   - Document success baseline for comparison
   - Specify technical requirements and success criteria
   - Add team plan with agent roles and responsibilities

3. **Generate Team Plan**
   - Backend Developer: Focus on failed command patterns
   - QA Engineer: Create test framework for validation
   - PM: Coordinate debugging and track progress

4. **Spawn Debugging Team**
   ```bash
   tmux-orc monitor stop
   tmux-orc orchestrator kill-all
   tmux-orc spawn pm --session mcp-reliability-fixes --briefing "[detailed briefing from planning directory]"
   ```

**CRITICAL**: All test results and documentation must go in the project-specific planning subdirectory. Never create loose files in root directory or planning/ root.

#### If All Tests Pass:
1. **Document Success**
   - Create success report in planning/completed/
   - Update system documentation
   - Mark MCP system as production-ready

2. **Archive Previous Issues**
   - Move old MCP debugging sessions to completed/
   - Update CLAUDE.md with current status

### Phase 5: Monitoring & Validation

#### Continuous Monitoring Setup:
- Schedule periodic re-runs of comprehensive test
- Integration with CI/CD for MCP regression testing
- Documentation updates for any new MCP commands

#### Success Metrics:
- **Target:** 100% MCP command reliability
- **Baseline:** Current success rate to be determined
- **Critical:** All agent coordination commands working
- **Enhanced:** Advanced features (tasks, recovery, etc.) working

## Usage Examples

### Manual Execution:
```
"Run mcp-comprehensive-test"
```

### Automated Scheduling:
```
"Set up weekly mcp-comprehensive-test runs"
```

### Post-Development:
```
"After MCP server changes, run mcp-comprehensive-test"
```

## Expected Outputs

1. **Planning Directory:** `.tmux_orchestrator/planning/[timestamp]-mcp-reliability-fixes/`
2. **Test Results Document:** `briefing.md` in planning directory (NOT root directory)
3. **Active Team:** Debugging team spawned and working on fixes
4. **Status Update:** TodoWrite progress tracking
5. **Technical Analysis:** Comprehensive analysis in planning subdirectory

## Integration Points

- **With Development Workflow:** Run after mcp_server.py changes
- **With CI/CD:** Automated testing in development pipeline
- **With Documentation:** Update MCP guides based on test results
- **With Monitoring:** Integration with system health checks

## Command Dependencies

- `tmux-orc reflect` - CLI structure discovery
- `mcp__tmux-orchestrator__*` - All MCP tools
- `TodoWrite` - Progress tracking
- `planning/` directory structure - Documentation
- Team spawning capabilities - Issue resolution

## Test Automation Script

To automate the complete test suite, use this approach:

```python
# Example test automation structure
commands_to_test = extract_all_commands_from_reflect()
results = []

for command in commands_to_test:
    mcp_result = test_mcp_command(command)
    cli_result = test_cli_command(command)

    results.append({
        'command': command,
        'mcp_success': mcp_result.success,
        'cli_success': cli_result.success,
        'parity': compare_results(mcp_result, cli_result)
    })

generate_report(results)
```

## Notes

- This test covers 100+ individual command variants
- Each command group has multiple actions/subcommands
- Total coverage includes all commands discovered via `tmux-orc reflect`
- Tests should be run in batches to avoid overwhelming the system
- Consider creating test fixtures for commands that require existing resources
