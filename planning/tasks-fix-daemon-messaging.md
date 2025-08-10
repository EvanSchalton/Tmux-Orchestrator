# Task List: Fix Critical Daemon and Message Delivery Issues

## Phase 1: Research & Discovery (2 hours)

### 1.1 Analyze Claude Terminal Interface
- [ ] Test manual message submission in Claude tmux session
- [ ] Document exact key sequences that work manually
- [ ] Identify differences between manual and programmatic submission
- [ ] Test timing requirements between keystrokes

### 1.2 Test Key Combinations
- [ ] Test standard terminal sequences: `C-m`, `\n`, `\r`, `Enter`
- [ ] Test special key combinations: `C-j`, `C-d`, escape sequences
- [ ] Test with different timing delays between keys
- [ ] Document all test results

### 1.3 Research Alternative Approaches
- [ ] Investigate if Claude has API endpoint for terminal sessions
- [ ] Research xdotool or similar automation tools
- [ ] Consider clipboard-based submission methods
- [ ] Evaluate file-based message passing as fallback

## Phase 2: Implementation (4 hours)

### 2.1 Update ClaudeInterface Class
- [ ] Implement working submission method based on research
- [ ] Add retry logic with different methods
- [ ] Add verification to confirm submission
- [ ] Add comprehensive logging for debugging

### 2.2 Fix TMUXManager.send_message
- [ ] Update to use new ClaudeInterface methods
- [ ] Add message delivery confirmation
- [ ] Implement timeout handling
- [ ] Add fallback to alternative methods

### 2.3 Create Test Utilities
- [ ] Build test script for message submission
- [ ] Create verification tool to confirm delivery
- [ ] Add debug mode for troubleshooting
- [ ] Document usage instructions

## Phase 3: Testing & Validation (2 hours)

### 3.1 Direct Message Testing
- [ ] Test `tmux-orc agent send` command
- [ ] Verify messages are submitted and processed
- [ ] Test with various message types and lengths
- [ ] Confirm no regressions in other commands

### 3.2 Monitoring Daemon Testing
- [ ] Deploy test agents
- [ ] Trigger idle conditions
- [ ] Verify PM receives notifications
- [ ] Confirm notifications are actionable

### 3.3 Recovery System Testing
- [ ] Simulate agent crashes
- [ ] Verify detection and recovery
- [ ] Test idle agent wake-up
- [ ] Validate full automation loop

### 3.4 Integration Testing
- [ ] Test inter-agent communication
- [ ] Verify initial briefing delivery
- [ ] Test full workflow end-to-end
- [ ] Document any remaining issues

## Phase 4: Documentation & Rollout (1 hour)

### 4.1 Update Documentation
- [ ] Document new submission method
- [ ] Update troubleshooting guide
- [ ] Add known limitations
- [ ] Create migration notes

### 4.2 Release Preparation
- [ ] Run full test suite
- [ ] Update version number
- [ ] Create release notes
- [ ] Push fixes to repository

## Priority Order
1. Research Claude submission methods (CRITICAL)
2. Implement working solution
3. Test with monitoring daemon
4. Validate recovery system
5. Full integration testing

## Success Criteria
- [ ] Messages reliably submitted to Claude agents
- [ ] Monitoring notifications delivered to PM
- [ ] Agent recovery fully automated
- [ ] No manual intervention required
