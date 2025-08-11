#!/usr/bin/env python3
"""Emergency fix for stuck Claude agents with unsubmitted messages."""

import time
from tmux_orchestrator.utils.tmux import TMUXManager

def diagnose_and_fix_stuck_agents():
    """Diagnose and fix agents with stuck messages."""
    tmux = TMUXManager()
    
    # Get all active agents
    try:
        agents = tmux.list_agents()
        print(f"Found {len(agents)} agents to check")
    except Exception as e:
        print(f"Error getting agent list: {e}")
        return
    
    for agent in agents:
        target = f"{agent['session']}:{agent['window']}"
        print(f"\n=== Checking {target} ===")
        
        try:
            # Capture current pane content
            content = tmux.capture_pane(target, lines=50)
            if not content:
                print(f"  No content found for {target}")
                continue
                
            # Check for Claude interface
            has_claude = any(indicator in content for indicator in [
                "│ >", "assistant:", "Human:", "? for shortcuts", "Bypassing Permissions"
            ])
            
            if not has_claude:
                print(f"  No Claude interface detected for {target}")
                continue
                
            print(f"  Claude interface detected for {target}")
            
            # Look for text in the input box
            lines = content.strip().split('\n')
            input_content = ""
            in_input_box = False
            
            for line in lines:
                if "│ >" in line:
                    # Extract content after the prompt
                    parts = line.split("│ >", 1)
                    if len(parts) > 1:
                        input_content += parts[1]
                    in_input_box = True
                elif in_input_box and line.startswith("│"):
                    # Continue collecting input box content
                    content_part = line[1:-1] if line.endswith("│") else line[1:]
                    input_content += content_part
                elif "╰─" in line:
                    # End of input box
                    in_input_box = False
            
            input_content = input_content.strip()
            
            if input_content:
                print(f"  STUCK MESSAGE DETECTED: '{input_content[:50]}...'")
                print(f"  Attempting to submit stuck message...")
                
                # Multiple submission attempts with different methods
                methods = [
                    ("C-Enter", "C-Enter"),
                    ("Enter twice", ["Enter", "Enter"]),  
                    ("Clear and retry", ["C-u", "C-Enter"]),
                ]
                
                for method_name, keys in methods:
                    print(f"    Trying {method_name}...")
                    
                    if isinstance(keys, list):
                        for key in keys:
                            tmux.send_keys(target, key)
                            time.sleep(0.5)
                    else:
                        tmux.send_keys(target, keys)
                        time.sleep(1)
                    
                    # Check if message was submitted
                    time.sleep(2)
                    new_content = tmux.capture_pane(target, lines=10)
                    if new_content != content:
                        print(f"    ✅ {method_name} worked - content changed")
                        break
                else:
                    print(f"    ❌ All methods failed for {target}")
            else:
                print(f"  No stuck message detected in input box")
                
        except Exception as e:
            print(f"  Error processing {target}: {e}")

if __name__ == "__main__":
    print("Emergency Stuck Agent Fixer")
    print("=" * 40)
    diagnose_and_fix_stuck_agents()
    print("\nDone!")