# Hard Files Priority List - Strategic Conversion Order

## Overview: 20 Hard Files (50 classes remaining)

After completing the 4 quick wins, Backend Dev should tackle hard files in this strategic order:

## 🥇 TIER 1: Single Class Files (Start Here - 9 files)

**Strategy**: Build momentum with single-class conversions using established patterns

1. **tests/test_server/test_tools/broadcast_message_test.py** ⏱️ 25 mins
   - **Classes**: 1 class, 12 functions
   - **Pattern**: Server tool testing

2. **tests/test_server/test_tools/get_messages_test.py** ⏱️ 25 mins
   - **Classes**: 1 class, 12 functions
   - **Pattern**: Message handling

3. **tests/test_core/error_handler_test.py** ⏱️ 30 mins
   - **Classes**: 1 class, 16 functions
   - **Pattern**: Error handling core logic

4. **tests/test_server/test_tools/assign_task_test.py** ⏱️ 35 mins
   - **Classes**: 1 class, 19 functions
   - **Pattern**: Task assignment

5. **tests/test_server/test_tools/create_pull_request_test.py** ⏱️ 35 mins
   - **Classes**: 1 class, 19 functions
   - **Pattern**: Git operations

6. **tests/test_server/test_tools/run_quality_checks_test.py** ⏱️ 40 mins
   - **Classes**: 1 class, 20 functions
   - **Pattern**: Quality assurance

7. **tests/test_server/test_tools/handoff_work_test.py** ⏱️ 40 mins
   - **Classes**: 1 class, 21 functions
   - **Pattern**: Work handoff

8. **tests/test_server/test_tools/track_task_status_test.py** ⏱️ 40 mins
   - **Classes**: 1 class, 21 functions
   - **Pattern**: Task tracking

9. **tests/test_server/test_tools/create_team_test.py** ⏱️ 45 mins
   - **Classes**: 1 class, 23 functions
   - **Pattern**: Team creation

**Tier 1 Total: ~315 minutes (5.25 hours) for 9 files, 9 classes**

## 🥈 TIER 2: Two-Class Files (Medium Complexity - 6 files)

10. **tests/rate_limit_test.py** ⏱️ 45 mins
    - **Classes**: 2 classes, 10 functions
    - **Pattern**: Rate limiting logic

11. **tests/test_server/mcp_server_test.py** ⏱️ 50 mins
    - **Classes**: 2 classes, 11 functions
    - **Pattern**: MCP server testing

12. **tests/test_core/performance_optimizer_test.py** ⏱️ 55 mins
    - **Classes**: 2 classes, 16 functions
    - **Pattern**: Performance optimization

13. **tests/test_server/test_tools/get_session_status_test.py** ⏱️ 60 mins
    - **Classes**: 2 classes, 17 functions
    - **Pattern**: Session status

14. **tests/test_server/test_tools/kill_agent_test.py** ⏱️ 50 mins
    - **Classes**: 1 class, 10 functions *(Note: Verify this count)*

15. **tests/test_server/test_tools/send_message_test.py** ⏱️ 55 mins
    - **Classes**: 1 class, 16 functions *(Note: Verify this count)*

**Tier 2 Total: ~315 minutes (5.25 hours) for 6 files, ~10 classes**

## 🥉 TIER 3: Three-Class Files (Higher Complexity - 4 files)

16. **tests/simplified_restart_system_test.py** ⏱️ 60 mins
    - **Classes**: 3 classes, 10 functions
    - **Pattern**: System restart logic

17. **tests/test_server/routes_basic_test.py** ⏱️ 65 mins
    - **Classes**: 3 classes, 11 functions
    - **Pattern**: Route handling

18. **tests/test_server/test_tools/schedule_checkin_test.py** ⏱️ 75 mins
    - **Classes**: 3 classes, 25 functions
    - **Pattern**: Scheduling operations

**Tier 3 Subtotal: ~200 minutes (3.3 hours) for 3 files, 9 classes**

## 🏆 TIER 4: Multi-Class Complex Files (Save for Last - 2 files)

19. **tests/test_core/test_recovery/detect_failure_test.py** ⏱️ 90 mins
    - **Classes**: 4 classes, 13 functions
    - **Pattern**: Failure detection (moved from quick wins)

20. **tests/test_server/test_tools/get_agent_status_test.py** ⏱️ 90 mins
    - **Classes**: 5 classes, 30 functions
    - **Pattern**: Complex agent status

21. **tests/test_server/test_tools/report_activity_test.py** ⏱️ 2 hours
    - **Classes**: 6 classes, 34 functions
    - **Pattern**: Activity reporting

## 🎯 FINAL BOSS: The Ultimate Challenge

22. **tests/monitor_helpers_test.py** ⏱️ 3-4 hours
    - **Classes**: 10 classes, 46 functions
    - **Complexity**: MAXIMUM - largest and most complex file
    - **Strategy**: Save for when all patterns are mastered
    - **Approach**: Break into multiple sessions if needed

**Tier 4 Total: ~7-8 hours for 4 files, 25 classes**

## 📊 Strategic Summary

### Total Hard Files Effort:
- **Tier 1** (9 single-class): 5.25 hours → **Build momentum**
- **Tier 2** (6 two-class): 5.25 hours → **Apply learned patterns**
- **Tier 3** (3 three-class): 3.3 hours → **Handle complexity**
- **Tier 4** (4 multi-class): 7-8 hours → **Master the complex**

**Total Estimated: 20-22 hours across multiple sessions**

### Success Strategy:
1. **Start with Tier 1** - Build confidence with single classes
2. **Master server tool patterns** - Many files follow similar patterns
3. **Apply three-tier fixture architecture** - Reuse established patterns
4. **Save monitor_helpers_test.py for last** - When all skills are honed

This systematic approach ensures steady progress while building expertise for the most challenging conversions.
