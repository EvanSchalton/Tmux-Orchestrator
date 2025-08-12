Change detection algorithms

1. Active
 - Polling strategy, pool every 300ms for 1.2s and perform a livenstine distance calculation between successive polls - if the distance is >1 the terminal is actively thinking
 - "Compacting conversation" is also an indicator

2. Crashed
__Maybe__ that the terminal_str.strip().endswith("$")

3. Error
?

4. Idle
Not Active (#1) & contains empty input box:
regex pattern = `\╭─*\╮\n\│\s\>\s*\│\n\╰─*\╯`

5. Message Queued
I'm not sure what the regex pattern would be but something like
`\╭─*\╮\n\│\s\>\s(.*?)\│` where the group != `\s*`
