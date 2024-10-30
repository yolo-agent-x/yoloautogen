# from .util import get_app_root
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from alembic import command, util
from alembic.config import Config
from loguru import logger

# from ..utils.db_utils import get_db_uri
from sqlmodel import Session, create_engine, text

from autogen.agentchat import AssistantAgent

from ..datamodel import (
    Agent,
    AgentConfig,
    AgentType,
    CodeExecutionConfigTypes,
    Model,
    Skill,
    Workflow,
    WorkflowAgentLink,
    WorkFlowType,
    Tool,
)

default_system_message = """
     You are responsible for extracting accurate parameters necessary for ToolAgent’s task execution.
     !!IMPORTANT!! You should try your best to extract the correct parameters from the request.
     !!IMPORTANT!!If information is insufficient or unclear, they must request clarification from the user, ending each query with "TERMINATE".
     Once the task results are received, they review and verify the completion before passing the summary to the UserProxy. The final summary after all steps should also end with "TERMINATE".
     !!IMPORTANT!! please use korean when you ask

     Few-Shot Example:

     1) User Input:
     "Check today's weather in Seoul."
     Agent: Extracts like {"location":"seoul"} and forwards to ToolAgent "

     2) Check for missing parameters
     "Book a table at the nearest Italian restaurant."
     Agent: Identifies missing information and requests clarification from the user "Could you specify the number of people and time for the reservation? TERMINATE"

     3) Check for specific parameters:
     "Get the latest news."        
     Agent: Requests further clarification from the user "Could you specify the news category or region of interest? TERMINATE"

     4) After Task Completion:
     After all steps are completed, Parameter Agent provides a final summary to the user
     Agent: Requested tasks have been completed. The weather was checked, and your reservation was made. TERMINATE
     """


def workflow_from_id(workflow_id: int, dbmanager: Any):
    workflow = dbmanager.get(Workflow, filters={"id": workflow_id}).data
    if not workflow or len(workflow) == 0:
        raise ValueError("The specified workflow does not exist.")
    workflow = workflow[0].model_dump(mode="json")
    workflow_agent_links = dbmanager.get(WorkflowAgentLink, filters={"workflow_id": workflow_id}).data

    def dump_agent(agent: Agent):
        exclude = []
        if agent.type != AgentType.groupchat:
            exclude = [
                "admin_name",
                "messages",
                "max_round",
                "admin_name",
                "speaker_selection_method",
                "allow_repeat_speaker",
            ]
        return agent.model_dump(warnings=False, mode="json", exclude=exclude)

    def get_agent(agent_id):
        with Session(dbmanager.engine) as session:
            agent: Agent = dbmanager.get_items(Agent, filters={"id": agent_id}, session=session).data[0]
            agent_dict = dump_agent(agent)
            agent_dict["skills"] = [Skill.model_validate(skill.model_dump(mode="json")) for skill in agent.skills]
            agent_dict["tools"] = [Tool.model_validate(tool.model_dump(mode="json")) for tool in agent.tools]
            model_exclude = [
                "id",
                "agent_id",
                "created_at",
                "updated_at",
                "user_id",
                "description",
            ]
            models = [model.model_dump(mode="json", exclude=model_exclude) for model in agent.models]
            agent_dict["models"] = [model.model_dump(mode="json") for model in agent.models]

            if len(models) > 0:
                agent_dict["config"]["llm_config"] = agent_dict.get("config", {}).get("llm_config", {})
                llm_config = agent_dict["config"]["llm_config"]
                if llm_config:
                    llm_config["config_list"] = models
                agent_dict["config"]["llm_config"] = llm_config
            agent_dict["agents"] = [get_agent(agent.id) for agent in agent.agents]
            return agent_dict

    agents = []
    for link in workflow_agent_links:
        agent_dict = get_agent(link.agent_id)
        agents.append({"agent": agent_dict, "link": link.model_dump(mode="json")})
        # workflow[str(link.agent_type.value)] = agent_dict
    if workflow["type"] == WorkFlowType.sequential.value:
        # sort agents by sequence_id in link
        agents = sorted(agents, key=lambda x: x["link"]["sequence_id"])
    workflow["agents"] = agents
    return workflow


def run_migration(engine_uri: str):
    database_dir = Path(__file__).parent
    script_location = database_dir / "migrations"

    engine = create_engine(engine_uri)
    buffer = open(script_location / "alembic.log", "w")
    alembic_cfg = Config(stdout=buffer)
    alembic_cfg.set_main_option("script_location", str(script_location))
    alembic_cfg.set_main_option("sqlalchemy.url", engine_uri)

    print(f"Running migrations with engine_uri: {engine_uri}")

    should_initialize_alembic = False
    with Session(engine) as session:
        try:
            session.exec(text("SELECT * FROM alembic_version"))
        except Exception:
            logger.info("Alembic not initialized")
            should_initialize_alembic = True
        else:
            logger.info("Alembic already initialized")

    if should_initialize_alembic:
        try:
            logger.info("Initializing alembic")
            command.ensure_version(alembic_cfg)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic initialized")
        except Exception as exc:
            logger.error(f"Error initializing alembic: {exc}")
            raise RuntimeError("Error initializing alembic") from exc

    logger.info(f"Running DB migrations in {script_location}")

    try:
        buffer.write(f"{datetime.now().isoformat()}: Checking migrations\n")
        command.check(alembic_cfg)
    except Exception as exc:
        if isinstance(exc, (util.exc.CommandError, util.exc.AutogenerateDiffsDetected)):
            try:
                command.upgrade(alembic_cfg, "head")
                time.sleep(3)
            except Exception as exc:
                logger.error(f"Error running migrations: {exc}")

    try:
        buffer.write(f"{datetime.now().isoformat()}: Checking migrations\n")
        command.check(alembic_cfg)
    except util.exc.AutogenerateDiffsDetected as exc:
        logger.info(f"AutogenerateDiffsDetected: {exc}")
        # raise RuntimeError(
        #     f"There's a mismatch between the models and the database.\n{exc}")
    except util.exc.CommandError as exc:
        logger.error(f"CommandError: {exc}")
        # raise RuntimeError(f"Error running migrations: {exc}")


def init_db_samples(dbmanager: Any):
    workflows = dbmanager.get(Workflow).data
    workflow_names = [w.name for w in workflows]
    if "YOLO Workflow" in workflow_names and "YOLO Workflow" in workflow_names:
        logger.info("Database already initialized with YOLO Workflow")
        return
    logger.info("Initializing database with YOLO Workflow")

    # models
    gpt_4o_mini = Model(
        model="gpt-4o-mini",
        description="OpenAI gpt-4o-mini model",
        user_id="guestuser@gmail.com",
        api_type="open_ai",
        api_key=os.getenv("OPEN_KEY"),
    )

    # skills
    confluence_search = Skill(
        name="confluence_search",
        description="Confluence search by query.",
        user_id="guestuser@gmail.com",
        libraries=["requests"],
        content="""import requests


def confluence_search(query: str) -> dict:
    return requests.get(
        "http://localhost:7700/plugin/api/v1/confluence/search",
        params={"query": query},
        headers={"Authorization": "Bearer token-123"},
    ).json()
""",
    )

    jira_issue_create = Skill(
        name="jira_issue_create",
        description="Jira Issue Create",
        user_id="guestuser@gmail.com",
        libraries=["requests"],
        content="""import requests


def jira_issue_create(title: str, description: str) -> dict:
    json = {
        "projectKey": "GAI21",
        "summary": title,
        "description": description,
        "issuetype": "Story",
    }
    return requests.post(
        "http://localhost:7700/plugin/api/v1/jira/create",
        json=json,
        headers={"Authorization": "Bearer token-123"},
    ).json()
""",
    )

    send_knox_email = Skill(
        name="send_knox_email",
        description="Knox Email Send",
        user_id="guestuser@gmail.com",
        libraries=["requests"],
        content="""import requests


def send_knox_email(
    sender: str, recipients: list[str], title: str, content: str
) -> str:
    json = {
        "sender": sender,
        "recipients": recipients,
        "title": title,
        "content": content,
    }
    return requests.post(
        "http://localhost:7700/plugin/api/v1/knox/send-mail",
        json=json,
        headers={"Authorization": "Bearer token-123"},
    ).json()""",
    )

    search_employee = Skill(
        name="search_employee",
        description="Search employee",
        user_id="guestuser@gmail.com",
        libraries=["requests"],
        content="""import requests

def search_employee(nickname: str) -> dict:
    params = {"nickname": nickname}
    return requests.get(
        "http://localhost:7700/plugin/api/v1/knox/search-employee",
        params=params,
        headers={"Authorization": "Bearer token-123"},
    ).json()
""",
    )

    summary_content = Skill(
        name="summary_content",
        description="Summary Content",
        user_id="guestuser@gmail.com",
        libraries=["requests"],
        content="""import requests


def summary_content(content: str) -> str:
    json = {
        "content": content,
    }
    return requests.post(
        "/summary", json=json, headers={"Authorization": "Bearer token-123"}
    ).json()
""",
    )

    # tools
    confluence_search_tool = Tool(
        name="confluence_search_tool",
        description="Confluence Search",
        user_id="guestuser@gmail.com",
        method="get",
        url="http://localhost:7700/plugin/api/v1/confluence/search",
        args_info={"query": "str"},
        auth_provider_id="confluence"
    )

    jira_issue_create_tool = Tool(
        name="jira_issue_create_tool",
        description="Jira Issue Create",
        user_id="guestuser@gmail.com",
        method="post",
        url="http://localhost:7700/plugin/api/v1/jira/create",
        args_info={
                        "summary": "str",
                        "description": "str",
                        "projectKey": "str | None = 'GAI21'",
                        "issuetype": "str | None = 'Story'",
                    },
        auth_provider_id="jira"
    )

    search_employee_tool = Tool(
        name="search_employee_tool",
        description="Search knox employee information.",
        user_id="guestuser@gmail.com",
        method="get",
        url="http://localhost:7700/plugin/api/v1/knox/search-employee",
        args_info={"nickname": "str"},
        auth_provider_id="knox"
    )

    send_knox_email_tool = Tool(
        name="send_knox_email_tool",
        description="Send Knox mail",
        user_id="guestuser@gmail.com",
        method="post",
        url="http://localhost:7700/plugin/api/v1/knox/send-mail",
        args_info={
                        "recipients": "list[str]",
                        "title": "str",
                        "content": "str",
                        "sender": "str = 'yolo@yolo.com'",
                    },
        auth_provider_id="knox"
    )

    summary_content_tool = Tool(
        name="summary_content_tool",
        description="Summary Content Tool",
        user_id="guestuser@gmail.com",
        method="post",
        url="http://localhost:7700/plugin/api/v1/summary",
        args_info={"content": "str"},
        auth_provider_id="summary"
    )

    # agents

    user_proxy_config = AgentConfig(
        name="user_proxy_agent",
        description="User Proxy Agent Configuration",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="You are a helpful assistant",
        code_execution_config=CodeExecutionConfigTypes.local,
        default_auto_reply="",
        llm_config={
            "temperature": 0
        },
    )
    user_proxy_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.userproxy, config=user_proxy_config.model_dump(mode="json")
    )

    tool_config = AgentConfig(
        name="tool_agent",
        description="Tool Agent Configuration",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="""
        The ToolAgent executes tasks based on specific parameters provided by the Parameter Agent and returns the results to the requesting agent.
        The ToolAgent does not modify parameters or request clarification; it focuses solely on executing the task as directed and returning the outcome.
        You only execute single function at once. 
        """,
        code_execution_config=CodeExecutionConfigTypes.none,
        default_auto_reply="TERMINATE",
        llm_config={
            "temperature": 0
        },
    )
    tool_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.assistant, config=tool_config.model_dump(mode="json")
    )

    confluence_agent_config = AgentConfig(
        name="confluence_agent",
        description="Confluence Assistant Agent. Solve the problem related to confluence",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="You are a helpful Confluence assistant. You can help with searching in confluence." + default_system_message,
        code_execution_config=CodeExecutionConfigTypes.none,
        llm_config={
            "temperature": 0
        },
    )
    confluence_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.assistant, config=confluence_agent_config.model_dump(mode="json")
    )

    jira_agent_config = AgentConfig(
        name="jira_agent",
        description="Jira Assistant Agent. Solve the problem related to jira",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="You are a helpful Jira assistant. You can help with creating jira issue." + default_system_message,
        code_execution_config=CodeExecutionConfigTypes.none,
        llm_config={
            "temperature": 0
        },
    )
    jira_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.assistant, config=jira_agent_config.model_dump(mode="json")
    )

    knox_agent_config = AgentConfig(
        name="knox_agent",
        description="Knox Assistant Agent. Solve the problem related to knox",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="""
        You are a helpful Knox assistant. You can help with knox service (sending email, searching employee).
        !!IMPORTANT!! When sending an email, must use the Employee Search API to retrieve recipient information.
        !!IMPORTANT!! When you don't know who to send the email to, ask to User.
        """ + default_system_message,
        code_execution_config=CodeExecutionConfigTypes.none,
        llm_config={
            "temperature": 0
        },
    )
    knox_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.assistant, config=knox_agent_config.model_dump(mode="json")
    )

    summary_agent_config = AgentConfig(
        name="summary_agent",
        description="Summary Assistant Agent. Summary the content",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="You are a helpful summary assistant. You can help with creating summary content." + default_system_message,
        code_execution_config=CodeExecutionConfigTypes.none,
        llm_config={
            "temperature": 0
        },
    )
    summary_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.assistant, config=summary_agent_config.model_dump(mode="json")
    )

    # group chat agent
    yolo_groupchat_config = AgentConfig(
        name="yolo_groupchat",
        admin_name="groupchat",
        description="Group Chat Agent Configuration",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=25,
        system_message="You are a group chat manager",
        code_execution_config=CodeExecutionConfigTypes.none,
        default_auto_reply="TERMINATE",
        llm_config={
            "temperature": 0
        },
        speaker_selection_method="auto",
    )
    yolo_groupchat_agent = Agent(
        user_id="guestuser@gmail.com", type=AgentType.groupchat, config=yolo_groupchat_config.model_dump(mode="json")
    )

    # workflows
    yolo_workflow = Workflow(
        name="YOLO Workflow",
        description="yolo workflow",
        user_id="guestuser@gmail.com",
        sample_tasks=[
            "'Scaled Agile'로 confluence에서 검색한 후 해당 내용을 요약해서 jira 이슈로 생성 한 후 그 결과를 knox mail로 jason과 milo에게 보내줘."],
    )

    with Session(dbmanager.engine) as session:
        # model
        session.add(gpt_4o_mini)

        # skill
        # session.add(confluence_search)
        # session.add(jira_issue_create)
        # session.add(send_knox_email)
        # session.add(search_employee)
        # session.add(summary_content)

        # tool
        session.add(confluence_search_tool)
        session.add(jira_issue_create_tool)
        session.add(send_knox_email_tool)
        session.add(search_employee_tool)
        session.add(summary_content_tool)

        # agent
        session.add(user_proxy_agent)
        session.add(tool_agent)
        session.add(confluence_agent)
        session.add(jira_agent)
        session.add(knox_agent)
        session.add(summary_agent)
        session.add(yolo_groupchat_agent)

        session.add(yolo_workflow)
        session.commit()

        dbmanager.link(link_type="agent_model", primary_id=confluence_agent.id, secondary_id=gpt_4o_mini.id)
        dbmanager.link(link_type="agent_model", primary_id=jira_agent.id, secondary_id=gpt_4o_mini.id)
        dbmanager.link(link_type="agent_model", primary_id=knox_agent.id, secondary_id=gpt_4o_mini.id)
        dbmanager.link(link_type="agent_model", primary_id=summary_agent.id, secondary_id=gpt_4o_mini.id)

        # dbmanager.link(link_type="agent_skill", primary_id=confluence_agent.id, secondary_id=confluence_search.id)
        # dbmanager.link(link_type="agent_skill", primary_id=jira_agent.id, secondary_id=jira_issue_create.id)
        # dbmanager.link(link_type="agent_skill", primary_id=knox_agent.id, secondary_id=search_employee.id)
        # dbmanager.link(link_type="agent_skill", primary_id=knox_agent.id, secondary_id=send_knox_email.id)
        # dbmanager.link(link_type="agent_skill", primary_id=summary_agent.id, secondary_id=summary_content.id)

        # link agent to tool
        dbmanager.link(link_type="agent_tool", primary_id=confluence_agent.id, secondary_id=confluence_search_tool.id)
        dbmanager.link(link_type="agent_tool", primary_id=jira_agent.id, secondary_id=jira_issue_create_tool.id)
        dbmanager.link(link_type="agent_tool", primary_id=knox_agent.id, secondary_id=send_knox_email_tool.id)
        dbmanager.link(link_type="agent_tool", primary_id=knox_agent.id, secondary_id=search_employee_tool.id)
        dbmanager.link(link_type="agent_tool", primary_id=summary_agent.id, secondary_id=summary_content_tool.id)


        # link agents to travel groupchat agent

        dbmanager.link(link_type="agent_agent", primary_id=yolo_groupchat_agent.id, secondary_id=user_proxy_agent.id)
        dbmanager.link(link_type="agent_agent", primary_id=yolo_groupchat_agent.id, secondary_id=tool_agent.id)
        dbmanager.link(link_type="agent_agent", primary_id=yolo_groupchat_agent.id, secondary_id=confluence_agent.id)
        dbmanager.link(link_type="agent_agent", primary_id=yolo_groupchat_agent.id, secondary_id=jira_agent.id)
        dbmanager.link(link_type="agent_agent", primary_id=yolo_groupchat_agent.id, secondary_id=knox_agent.id)
        dbmanager.link(link_type="agent_agent", primary_id=yolo_groupchat_agent.id, secondary_id=summary_agent.id)

        dbmanager.link(link_type="agent_model", primary_id=yolo_groupchat_agent.id, secondary_id=gpt_4o_mini.id)

        dbmanager.link(
            link_type="workflow_agent", primary_id=yolo_workflow.id, secondary_id=user_proxy_agent.id,
            agent_type="sender"
        )
        dbmanager.link(
            link_type="workflow_agent",
            primary_id=yolo_workflow.id,
            secondary_id=yolo_groupchat_agent.id,
            agent_type="receiver",
        )
        logger.info("Successfully initialized database with YOLO Workflow")
