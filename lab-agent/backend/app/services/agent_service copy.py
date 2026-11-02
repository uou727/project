# 删除这一行！！ from unittest import result
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.config import settings
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.services import agent_tools

SYSTEM_PROMPT = """你是智能实验室预约系统的 Agent，回答要简洁。
你可以：
1. 使用 search_lab_docs 查询实验室的规则、安全、开放时间等问题
2. 使用 list_open_labs / list_lab_equipments  查询真实的实验室和设备
3. 再用户进行了预约确认后，使用 create_lab_reservation 来进行真实的预约落库
4. 使用 get_today 来进行日期的换算
## 必须遵守
当用户提到了 今天、明天、后天 等日期相关的问题，请先调用 get_today 来获取日期，**不要直接返回 我需要确定明天的具体日期**。
在提交预约之前必须向用户复述：实验室ID与名称（或设备ID和名称）、日期、开始时间、结束时间。并得到用户确认再进行实际操作。
用户没说【确认】【确认预约】【就这样预约】等确定性回复之前，不要调用 create_lab_reservation。
工作流的确认环节里如果缺少了 lab_id，请先 list_open_labs 查到了 lab_id 再创建，不要瞎写。
工作流的确认环节里如果缺少了 equipment_id，请先 list_lab_equipments 查到了 equipment_id 再创建，不要瞎写。
预约成功后状态是待审核，必须管理员确认后实验室（或设备）才能使用。
不要瞎编数据库里没有的实验室或者设备信息。
如果是问开放时间或者实验室规则，优先调用 search_lab_docs，不要凭空回复。
"""

TOOL_LABELS = {
    "search_lab_docs": "检索实验室知识库",
    "list_open_labs": "查询开放实验室",
    "list_lab_equipments": "查询实验室设备",
    "create_lab_reservation": "提交预约",
    "get_today": "获取今天日期",
}


def _build_history(data: ChatRequest) -> list:
    """前端的信息转化为 LangChain的消息对象"""
    history = []
    for message in data.messages:
        if message.role == "user" and message.content.strip():
            history.append(HumanMessage(content=message.content.strip()))
        elif message.role == "assistant" and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))
    if not history:
        raise BusinessException(message="请输入您的对话内容")
    return history


def build_agent(db: Session, current_user: User):
    tools = agent_tools.build_tools(db, current_user)
    llm = ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=0,  # 发散思维程度
        timeout=30,  # 增加请求超时，防止长连接僵死
        streaming=True,  # 流式输出 stream_event 接收到逐字返回的token
    ).bind_tools(tools)

    def agent_node(state: MessagesState):
        """langGraph 执行的工作流的节点"""
        response = llm.invoke(state["messages"])
        return {"messages": response}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)  # 调用大模型的节点
    graph.add_node("tools", ToolNode(tools))  # tool call的节点
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent", tools_condition
    )  # 看有无tool_call 有就继续 没有就END 输出
    graph.add_edge("tools", "agent")  # 让agent看tool调用的结果
    return graph.compile()


def run_agent(db: Session, current_user: User, data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")
    history = []
    for message in data.messages:
        if message.role == "user" and message.content.strip():
            history.append(HumanMessage(content=message.content.strip()))
        elif message.role == "assistant" and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    agent = build_agent(db, current_user)
    try:
        # ✅ 接住返回值！！！
        agent_result = agent.invoke(
            {"messages": [SystemMessage(content=SYSTEM_PROMPT), *history]},
            config={"recursion_limit": 10},  # 小写 config
        )
    except BusinessException:
        raise
    except Exception as e:
        # 调试用，可以后续删掉e
        raise BusinessException(message=f"大模型调用失败：{e!s}")

    # ✅ langgraph返回key是 messages 复数
    messages = agent_result.get("messages") or []

    if not messages:
        raise BusinessException(message="大模型没有任何的内容")

    # ✅ 修改循环变量名，避免覆盖
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content.strip():
            content = msg.content.strip()
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            if str(content).strip():
                return str(content).strip()
    # 兜底，如果遍历完没找到ai消息
    raise BusinessException(message="未获取到助手回复")
