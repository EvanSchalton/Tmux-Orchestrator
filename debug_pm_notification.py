#!/usr/bin/env python3
"""Debug the PM notification logic to find where it's failing."""

import sys
import logging
from datetime import datetime, timedelta
from tmux_orchestrator.utils.tmux import TMUXManager

def debug_pm_notification():
    """Step through the PM notification logic to find the failure point."""
    
    # Set up logging to see what's happening
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("debug")
    
    tmux = TMUXManager()
    target = "monitor-fixes:4"  # QA agent that should trigger notification
    
    print(f"=== Debugging PM notification for {target} ===")
    
    # Step 1: Check if we can find PM
    try:
        sessions = tmux.list_sessions()
        print(f"Found {len(sessions)} sessions")
        
        pm_target = None
        for session in sessions:
            print(f"  Checking session: {session['name']}")
            try:
                windows = tmux.list_windows(session["name"])
                for window in windows:
                    window_name = window.get("name", "").lower()
                    target_candidate = f"{session['name']}:{window['index']}"
                    print(f"    Window: {target_candidate} - {window_name}")
                    
                    # Check if this looks like a PM window
                    if any(pm_indicator in window_name for pm_indicator in ["pm", "manager", "project"]):
                        print(f"    → PM candidate found: {target_candidate}")
                        # Verify it has Claude interface
                        content = tmux.capture_pane(target_candidate, lines=10)
                        has_claude = any(indicator in content for indicator in ["│ >", "assistant:", "? for shortcuts"])
                        print(f"    → Has Claude interface: {has_claude}")
                        if has_claude:
                            pm_target = target_candidate
                            print(f"    → ✅ PM confirmed: {pm_target}")
                            break
            except Exception as e:
                print(f"    Error checking session {session['name']}: {e}")
        
        if not pm_target:
            print("❌ No PM found!")
            return
            
        # Step 2: Check self-notification logic
        if pm_target == target:
            print(f"❌ Would skip self-notification (PM={pm_target}, target={target})")
            return
        else:
            print(f"✅ Not self-notification (PM={pm_target}, target={target})")
        
        # Step 3: Test actual message sending
        message = f"TEST: Idle agent notification for {target}"
        print(f"Sending test message to PM: {message}")
        
        success = tmux.send_message(pm_target, message)
        if success:
            print("✅ Message send succeeded")
            
            # Verify PM received it
            import time
            time.sleep(2)
            pm_content = tmux.capture_pane(pm_target, lines=20)
            if "TEST: Idle agent notification" in pm_content:
                print("✅ PM received the message!")
            else:
                print("❌ PM did not receive the message")
        else:
            print("❌ Message send failed")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pm_notification()