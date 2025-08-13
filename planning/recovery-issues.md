1. ✅ FIXED: With the rate limits, those should always be <4 hours. It worked well last time and identified the rate limit and parsed the timestamp, but after recovering it re-read the rate limit and since it was for 12UTC and it was now 00:01 UTC it paused/waited for ~24hrs. We should guard against this by setting an upper limit (4hrs) and ignoring if the time delta is greater.

2. ✅ FIXED: The daemon misidentified the agent as crashed while the PM was starting up the agent, and again thought it was idle before it was given instructions. Maybe once a agent is identified as missing we can add it to another object in the daemon to ignore it in the idle/crash control loop for some period of time (e.g. 2 minutes) **don't use magic numbers**

3. ✅ FIXED: We need to update the template for telling the PM that an agent has gone missing to not tell it it *NEEDS* to restart the agent, instead tell it to review the team plan and restart if agent **IF** it is still needed. I want to avoid a scenario where the PM shuts down an agent that's no longer needed then rehydrates it just to realize it isn't needed again.

4. NEW: The daemon sends notifications immediately as issues are found, creating spam. We need to batch notifications per PM per monitoring cycle. See detailed plan at: /workspaces/Tmux-Orchestrator/.tmux_orchestrator/planning/monitor-notification-batching-plan.md

5. ✅ FIXED: The daemon doesn't respect session boundaries when finding PMs. When notifying about an idle agent, it should only look for a PM in the SAME SESSION as that agent. Currently it sends notifications to any PM it finds, causing cross-session notification pollution.
