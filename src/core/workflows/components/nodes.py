from src.core.workflows.components.states import WorkflowState


async def node_initialize(state: WorkflowState) -> dict:
    """Entry node – sets the first agent to run."""
    return {"next": "supervisor"}


def route_by_next(state: WorkflowState) -> str:
    """Conditional router – reads state['next'] to decide which node runs."""
    return state.get("next", "FINISH")


def node_run_agent(agent_name: str):
    """Factory: returns an async node function that runs the named agent."""

    async def _node(state: WorkflowState) -> dict:
        from src.core.agents.factory import AgentFactory
        from src.utils import load_config

        config = load_config()
        agent_config = config.get("agents", {}).get(agent_name, {})
        agent = AgentFactory.create(agent_name, agent_config)
        result = await agent.ainvoke(state)
        return result

    _node.__name__ = f"run_agent_{agent_name}"
    return _node
