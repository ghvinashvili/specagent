# Launch: the <run-name> run

The manager fills this file before every launch and sends its table to the owner in one message; each yes of the owner
is appended as a `Yes:` line. When the pre-flight's `live` check lists a busy session outside the run in the checkout,
the manager reads the list and appends `Live: <name>, <name> — <what each is>`. When the pre-flight has passed and the
first role starts, the manager appends `Launched: ` and the UTC time as `date -u +%Y-%m-%dT%H:%M:%SZ` prints it, once
(no relaunch, resume or hand-over changes it); the owner's surface takes the run's start from it. The pre-flight
(`scripts/manager/preflight.py check --yes` of the skill) holds the launch until every line below is filled and every
role it starts is named in a `Yes:` line. No model is named here: the roles read the run folder's `_*.md`, so the
models go in the manager's chat message only.

Purpose: <what the run builds, in one sentence, and the spec or plan it builds from>
Size: <n> tasks, or <n> items in units of <k> (the unit-size rule); <why one context cannot hold the work> (otherwise one session plus a verifier, and no table)
Model rule: <the rule the manager applies per role, stated without naming a model>
Estimate: <n> roles, <k> fresh sessions per unit, <n>-<m> sessions; from `~/vault/context/measurements/<date>-<run>.md` (the last run of the same shape): $<a>-$<b> per session, start-up read <t>k tokens per fresh session (`startup_report.py`); $<low>-$<high> per unit, $<total> for the run
Budget: $<amount> for the run; at $<amount> the manager launches nothing new and asks the owner
Usage: <the newest reading of _control/usage.json: each limit, its percentage, its reset time>

| role | lane | settings | skills | ECC texts | cost estimate |
|---|---|---|---|---|---|
| <project>/planner | plan | `_control/planner-settings.json` | <the skills its brief loads> | <the ECC texts of its brief> | $<n> |
| <project>/plan-fixer | plan | `_control/plan-fixer-settings.json` | <skills> | <ECC texts> | $<n> |
| <project>/critic | review | `_control/critic-settings.json` | <skills> | <ECC texts> | $<n> |
| <project>/builder-a | a | `_control/builder-a-settings.json` | <skills> | <ECC texts> | $<n> |
| <project>/builder-b | b | `_control/builder-b-settings.json` | <skills> | <ECC texts> | $<n> |
| <project>/verifier | checks | `_control/verifier-settings.json` | <skills> | <ECC texts> | $<n> |
| <project>/judge | end | `_control/judge-settings.json` | <skills> | <ECC texts> | $<n> |

The plan fixer's row is launched by the watcher on demand (`on_demand` in `_agents.json`), never at the start: the
manager launches every other row.

Yes: <YYYY-MM-DDTHH:MMZ> — <roles> — <what the owner approved, and one more session of a role when its queue grows>
