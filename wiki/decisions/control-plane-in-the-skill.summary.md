Decision (owner, 2026-10-29): the control plane lives in the skill.
The registry, the orders and the record monitor are files under the run folder's _control/, written by the skill's scripts.
The harness's state.json, harness poll and statusline.py are not extended to skill runs.
The roles stay blind to these files: _control/ sits behind the run folder's deny.
