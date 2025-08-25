# MCP Test Suite Restoration Project Plan

## Project Overview
The Tmux Orchestrator project has a significant number of disabled MCP tests (43 files) that were excluded due to outdated imports and deprecated architecture. This project aims to clean up the test suite, restore valuable tests, and ensure comprehensive test coverage for the current FastMCP implementation.

## Current State Assessment

### Git Status
- **Branch**: main (up to date)
- **Modified Files**: 
  - `.pre-commit-config.yaml`
  - `pytest.ini` 
  - Test files in `tests/unit/mcp/`
  - Configuration files
- **Untracked Files**:
  - `DISABLED_MCP_TESTS_REPORT.md`
  - `DISABLED_TESTS_ANALYSIS.md`
  - `bandit_results.json`
  - Test backup archive

### Test Suite Status
- **Disabled Tests**: 38 files in `tests/test_mcp_disabled/`
- **Reason**: Outdated imports referencing non-existent `tmux_orchestrator.server.tools.*`
- **Active MCP Tests**: Located in `tests/unit/mcp/` with good coverage
- **Key Issues**:
  - Tests reference deprecated server/tools architecture
  - Use old MCP API (`call_tool`, `list_tools`)
  - Test removed features and patterns

### Active Agents
- **test-restoration:2**: QA Engineer (active)
- **test-restoration:3**: Project Manager (idle)
- **test_mcp_disabled-frontend:3**: Frontend Dev 1 (active)
- **test_mcp_disabled-frontend:4**: Frontend Dev 2 (active)

## Project Goals

1. **Clean up disabled test directory** - Remove tests for deprecated architecture
2. **Restore valuable tests** - Update 5 identified tests for current implementation
3. **Ensure test coverage** - Verify current tests adequately cover MCP functionality
4. **Document changes** - Track what was removed and why
5. **Commit clean state** - Ensure repository is in good state

## Phase 1: Test Cleanup (Priority: HIGH)

### Tasks:
1. **Archive disabled tests** for historical reference
2. **Delete `tests/test_mcp_disabled/` directory** entirely
3. **Remove pytest.ini exclusion** for the deleted directory
4. **Document deletion rationale** in project history

### Deliverables:
- Archived test directory
- Clean test structure
- Updated pytest configuration

## Phase 2: Test Restoration (Priority: HIGH)

### Candidates for Update (5 files):
1. `test_mcp_integration.py` - Integration test scenarios
2. `test_mcp_protocol.py` - Protocol compliance tests
3. `test_mcp_cli_parity.py` - CLI parity testing
4. `test_api_integration_complete.py` - API integration patterns
5. `test_user_experience_validation.py` - UX validation

### Update Strategy:
- Extract test scenarios from archived files
- Rewrite for FastMCP implementation
- Update imports to use `tmux_orchestrator.mcp_server`
- Replace old API calls with current patterns
- Add to `tests/unit/mcp/` directory

## Phase 3: Test Coverage Verification (Priority: MEDIUM)

### Coverage Areas to Verify:
1. **FastMCP Protocol Compliance**
2. **Dynamic Tool Generation**
3. **CLI Reflection Accuracy**
4. **Error Handling**
5. **Performance Benchmarks**
6. **Integration Scenarios**

### Tasks:
- Run coverage analysis
- Identify gaps in current tests
- Create new tests for uncovered areas
- Ensure all MCP features tested

## Phase 4: Documentation & Commit (Priority: MEDIUM)

### Tasks:
1. **Update test documentation**
2. **Create migration guide** for future reference
3. **Clean up temporary files**:
   - Remove analysis reports
   - Remove backup archives
   - Clean bandit results
4. **Commit changes** with clear message

### Commit Strategy:
- Stage test deletions
- Stage test additions
- Stage configuration updates
- Create comprehensive commit message

## Risk Assessment

### Identified Risks:
1. **Test Coverage Gaps** - Deleting tests may remove valuable scenarios
   - *Mitigation*: Archive tests, extract valuable scenarios
   
2. **Breaking Active Tests** - Changes might affect working tests
   - *Mitigation*: Run full test suite after each change
   
3. **Configuration Issues** - pytest.ini changes might have side effects
   - *Mitigation*: Test configuration changes incrementally

## Timeline

### Week 1:
- Day 1-2: Test cleanup and archival
- Day 3-4: Test restoration and updates
- Day 5: Coverage verification

### Week 2:
- Day 1-2: Fill coverage gaps
- Day 3: Documentation
- Day 4: Final testing and commit
- Day 5: Buffer for issues

## Success Criteria

1. ✅ All disabled tests removed or updated
2. ✅ No references to deprecated architecture
3. ✅ Test suite passes completely
4. ✅ Coverage meets or exceeds previous levels
5. ✅ Clean git status achieved
6. ✅ Documentation updated

## Team Requirements

### Required Roles:
1. **QA Engineer** - Test analysis and verification
2. **Developer** - Test updates and rewrites
3. **Code Reviewer** - Ensure quality and standards

### Communication Plan:
- Daily status updates
- Immediate escalation of blockers
- Review checkpoints after each phase

## Next Steps

1. Review and approve this plan
2. Spawn required team members
3. Begin Phase 1 execution
4. Monitor progress and adjust as needed

---

**Project Manager Notes:**
- Current working directory restrictions noted
- Multiple agent sessions already active
- Consider consolidating efforts with existing agents