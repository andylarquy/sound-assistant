# Agent protocol

Not started. Agents currently talk to the control plane directly over
its REST API (see `server/api/`, `agents/windows/control.py`). A
dedicated schema/protocol here is deferred until a second agent
(`agents/linux`) exists and the REST API's actual requirements are
clearer - see DESIGN.md's "start simple" principle (section 23.7).
