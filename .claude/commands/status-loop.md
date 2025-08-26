# Status Loop Command

## Purpose
Monitor team progress with regular 115-second cycles, providing feedback and guidance to the PM.

## Instructions
1. **Start Timer**: Use `sleep 115` to begin each monitoring cycle
2. **Check Status**: After sleep completes, check team status using daemon monitoring or agent status commands
3. **Provide Feedback**: Send any needed guidance or feedback to the PM
4. **Reset Timer**: IMMEDIATELY set the next 115-second timer using `sleep 115` again
5. **Repeat**: Continue the loop indefinitely until mission completion

## Critical Loop Pattern
```bash
sleep 115
# Check status and provide PM feedback
sleep 115
# Check status and provide PM feedback
sleep 115
# Etc...
```

## Key Requirements
- **Always reset the timer** after providing feedback
- **Never break the 115-second rhythm**
- **Continuously monitor** until project closeout
- **Provide actionable guidance** to keep progress moving
