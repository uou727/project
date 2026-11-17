import json
import operator
import re
from collections.abc import AsyncIterator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Send
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.config import settings
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.services import agent_tools

AGENT_LABELS = {
    "lab": "实验室助手",
    "schedule": "课表助手",
    "study": "学习规划助手",
}

TOOL_LABELS = {
    "search_lab_docs": "检索实验室知识库",
    "list_open_labs": "查询开放实验室",
    "list_lab_equipments": "查询实验室设备",
    "create_lab_reservation": "提交预约",
    "get_today": "获取今天日期",
    "get_my_schedule": "查询课表",
    "get_my_study_plans": "读取学习计划",
    "get_my_free_slots": "分析空闲时间",
    "save_study_plan": "保存学习计划",
}

SUPERVISOR_PROMPT = """你是「实验室预约与学习规划系统」的调度器。
你的唯一任务是判断用户最后一句话涉及哪些领域，不要回答用户的问题。

可选领域：
- lab：实验室预约、开放时间、实验室规则、设备、取消预约
- schedule：课表、上课时间、课程名称、教室、某天有没有课
- study：学习计划、学习安排、复习规划、时间怎么分配

规则：
1. 可以同时选择多个领域，顺序无关。
2. 用户只是在打招呼、问你是谁这类与业务无关的话时，返回空数组。
3. 只输出 JSON，不要输出解释，也不要用 Markdown 代码块包裹。

输出格式：{"agents": ["lab"], "reason": "一句话理由"}

示例：
用户：我周三有课吗 -> {"agents": ["schedule"], "reason": "询问课表"}
用户：帮我约明天下午的实验室 -> {"agents": ["lab"], "reason": "预约实验室"}
用户：这周哪天没课，帮我把实验报告排进去 -> {"agents": ["schedule", "study"], "reason": "要课表也要规划"}
用户：周三上完课下午能去约实验室吗 -> {"agents": ["schedule", "lab"], "reason": "课表与预约都涉及"}
用户：你好 -> {"agents": [], "reason": "闲聊"}
"""

LAB_PROMPT = """你是实验室预约助手，只处理实验室相关的问题。

可用工具：
- search_lab_docs：检索实验室规则、安全规范、开放时间
- list_open_labs：查询开放的实验室，用来拿 lab_id
- list_lab_equipments：查询某个实验室下的设备
- create_lab_reservation：提交预约
- get_today：日期换算

必须遵守：
1. 用户提到今天、明天、后天、这周时，先调 get_today 换算成具体日期。
2. 问规则、安全或开放时间时优先调 search_lab_docs，不要凭记忆回答。
3. 不要编造数据库里没有的实验室或设备。
4. 预约前必须向用户复述实验室名称、日期、起止时间，得到明确确认后才能调 create_lab_reservation。
5. 缺少 lab_id 时先 list_open_labs 查，不要自己编 ID。
6. 你只负责实验室，课表和学习计划的问题不要作答。
"""

SCHEDULE_PROMPT = """你是课表查询助手，只负责回答当前学生自己的课表问题。

可用工具：
- get_my_schedule：查询自己的课表，可指定日期区间
- get_today：日期换算

必须遵守：
1. 用户提到今天、明天、后天、本周时，先调 get_today 再换算日期。
2. 只能查当前登录学生本人的课表，查不到别人的。
3. 回答时按日期排列，列出课程名、节次、具体时间、地点。
4. 没有排课就明确说明那几天没课，不要编造课程。
5. 你只负责课表，实验室预约和学习规划的问题不要作答。
"""

STUDY_PROMPT = """你是学习规划助手，帮学生把学习任务安排到真实的空闲时间里。

可用工具：
- get_my_study_plans：读学生已有的学习计划
- get_my_free_slots：查每天没课的时间段
- get_my_schedule：查具体课表
- save_study_plan：保存学习计划
- get_today：日期换算

必须遵守：
1. 给安排之前必须先调 get_my_free_slots 看真实空闲时间，不能凭空安排。
2. 先看 get_my_study_plans，尽量延续学生已有的目标和进度。
3. 建议要具体到「哪天几点到几点做什么」，并说明为什么选这个时段。
4. 只有用户明确说保存时才调 save_study_plan。
5. 你只负责学习规划，实验室预约不要作答。
"""

AGGREGATOR_PROMPT = """你是这个系统的总结助手，负责把各领域助手查到的结果整合成一段回答。

要求：
1. 只使用提供的事实，不要补充没查到的信息。
2. 问题涉及多个领域时，分段回答，让用户一眼看清每部分的结论。
3. 某个领域没有结果就说明没查到，不要编造。
4. 语气简洁，不要重复用户的问题。
5. 预约、保存计划这类写操作，提醒用户还需要确认或审核。
"""


class OrchestratorState(TypedDict):
    """多 Agent 编排的共享状态。

    messages：完整对话，只有 aggregator 会往里追加最终回答
    agents：supervisor 选中的专家
    results：各专家查到的结果，并行执行时用 operator.add 累加
    """

    messages: Annotated[list, add_messages]
    agents: list[str]
    results: Annotated[list[dict], operator.add]


def _make_llm(streaming: bool = True, temperature: float = 0):
    """创建 ChatOpenAI 客户端，统一从配置读 key / base_url / model。"""
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=temperature,
        timeout=60,  # 多 Agent 链路比单 Agent 长，超时放宽到 60 秒
        streaming=streaming,
    )


def _chunk_text(chunk: Any) -> str:
    """从模型流式 chunk 里抠出纯文本。
    content 有时是 str，有时是 [{type, text}, ...] 这种块列表，要统一成字符串。
    """
    if chunk is None:
        return ""
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text") or "")
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content) if content is not None else ""


def _tool_output_preview(output: Any, limit: int = 200) -> str:
    """把工具结果收成短预览，避免整段 JSON 刷到前端过程区。"""
    if isinstance(output, ToolMessage):
        output = output.content
    text = output if isinstance(output, str) else str(output)
    return text if len(text) <= limit else text[:limit] + "…"


def _build_history(data: ChatRequest) -> list:
    """前端只传 user/assistant 文本，转成 LangChain 消息对象。"""
    history = []
    for message in data.messages or []:
        if message.role == "user" and message.content.strip():
            history.append(HumanMessage(content=message.content.strip()))
        elif message.role == "assistant" and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))
    if not history:
        raise BusinessException(message="请输入您要对话的内容")
    return history


def _parse_agents(text: str) -> list[str]:
    """从 supervisor 的输出里取专家列表。

    解析失败时退回全部领域：宁可多跑几个专家，也不要漏答。
    解析成功但列表为空是合法结果（闲聊），此时直接交给汇总节点。
    """
    raw = text or ""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return list(AGENT_LABELS)
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return list(AGENT_LABELS)
    agents = payload.get("agents")
    if not isinstance(agents, list):
        return list(AGENT_LABELS)
    picked = [name for name in agents if name in AGENT_LABELS]
    # 去重但保留 supervisor 给出的顺序
    return list(dict.fromkeys(picked))


def _build_expert_graph(tools: list):
    """每个专家内部就是一个标准 ReAct 子图：agent ⇄ tools"""
    llm = _make_llm().bind_tools(tools)

    async def agent_node(state: MessagesState):
        """专家内部的单步决策：把当前消息交给绑定了工具的模型。"""
        response = await llm.ainvoke(state["messages"])
        return {"messages": response}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def _make_expert_node(name: str, prompt: str, tools: list):
    """把专家子图包装成编排图节点。

    入参是 Send 派发过来的 payload，返回 {"results": [...]}，
    多个专家并行时靠 operator.add 合并结果。
    """
    subgraph = _build_expert_graph(tools)

    async def node(payload: dict) -> dict:
        """执行专家子图，取最后一条消息作为该领域的结果。"""
        result = await subgraph.ainvoke(
            {"messages": [SystemMessage(content=prompt), *payload["messages"]]},
            config={"recursion_limit": 8},  # 专家内部别空转太久
        )
        text = _chunk_text(result["messages"][-1])
        return {
            "results": [
                {
                    "agent": name,
                    "label": AGENT_LABELS[name],
                    "content": text or "没有查到相关内容",
                }
            ]
        }

    return node


def _route_to_experts(state: OrchestratorState):
    """按 supervisor 的结论并行派发。

    返回空列表会被当成「图结束」，所以闲聊时显式派给 aggregator。
    """
    agents = state.get("agents") or []
    if not agents:
        return [Send("aggregator", {"messages": state["messages"], "results": []})]
    return [
        Send(f"{name}_expert", {"messages": state["messages"]})
        for name in agents
        if name in AGENT_LABELS
    ]


def _attach_digest(messages: list, digest: str) -> list:
    """把专家结果并到最后一条用户消息里，保持 human/assistant 交替合法"""

    def merge(text: str) -> str:
        """把用户原问题和专家事实拼成一条消息，供汇总节点使用。"""
        return f"{text}\n\n【各领域助手查到的事实】\n{digest}"

    if not messages:
        return [HumanMessage(content=merge(""))]
    last = messages[-1]
    if isinstance(last, HumanMessage):
        return [*messages[:-1], HumanMessage(content=merge(last.content))]
    return [*messages, HumanMessage(content=merge(""))]


def build_orchestrator(db: Session, current_user: User):
    """supervisor 路由 + 专家并行 + 汇总输出"""
    lab_node = _make_expert_node(
        "lab", LAB_PROMPT, agent_tools.build_lab_tools(db, current_user)
    )
    schedule_node = _make_expert_node(
        "schedule", SCHEDULE_PROMPT, agent_tools.build_schedule_tools(db, current_user)
    )
    study_node = _make_expert_node(
        "study", STUDY_PROMPT, agent_tools.build_study_tools(db, current_user)
    )

    supervisor_llm = _make_llm(streaming=False)
    aggregator_llm = _make_llm()

    async def supervisor_node(state: OrchestratorState) -> dict:
        """调度节点：只读最近 6 条消息，判断该派哪些专家。"""
        # 只带最近几轮，够判断意图，也避免历史太长拖慢路由
        recent = state["messages"][-6:]
        response = await supervisor_llm.ainvoke(
            [SystemMessage(content=SUPERVISOR_PROMPT), *recent]
        )
        return {"agents": _parse_agents(_chunk_text(response))}

    async def aggregator_node(state: OrchestratorState) -> dict:
        """汇总节点：把各专家结果拼进上下文，生成最终回答。"""
        results = state.get("results") or []
        messages = [SystemMessage(content=AGGREGATOR_PROMPT), *state["messages"]]
        if results:
            digest = "\n\n".join(
                f"【{item['label']}】\n{item['content']}" for item in results
            )
            messages = _attach_digest(messages, digest)
        response = await aggregator_llm.ainvoke(messages)
        return {"messages": response}

    graph = StateGraph(OrchestratorState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("lab_expert", lab_node)
    graph.add_node("schedule_expert", schedule_node)
    graph.add_node("study_expert", study_node)
    graph.add_node("aggregator", aggregator_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", _route_to_experts)
    # 并行分支全部汇到 aggregator，LangGraph 会等已调度的专家都跑完
    for expert in ("lab_expert", "schedule_expert", "study_expert"):
        graph.add_edge(expert, "aggregator")
    graph.add_edge("aggregator", END)
    return graph.compile()


async def stream_agent(
    db: Session, current_user: User, data: ChatRequest
) -> AsyncIterator[dict]:
    """生成器：边跑编排图边 yield 事件，供 SSE 推给前端。

    事件类型：status / agent_start / tool_start / tool_end / token / done / error
    """
    try:
        history = _build_history(data)
        orchestrator = build_orchestrator(db, current_user)
        inputs = {"messages": history, "agents": [], "results": []}
        yield {"type": "status", "message": "正在分析问题…"}

        async for event in orchestrator.astream_events(
            inputs,
            version="v2",
            config={"recursion_limit": 25},  # supervisor + 专家子图 + 汇总，步数放宽
        ):
            kind = event.get("event")
            name = event.get("name") or ""

            if kind == "on_chain_end" and name == "supervisor":
                output = (event.get("data") or {}).get("output")
                agents = output.get("agents") if isinstance(output, dict) else None
                if agents:
                    yield {
                        "type": "agent_start",
                        "agents": [
                            {"name": item, "label": AGENT_LABELS[item]} for item in agents
                        ],
                    }
            elif kind == "on_tool_start":
                yield {
                    "type": "tool_start",
                    "name": name,
                    "label": TOOL_LABELS.get(name, name),
                }
            elif kind == "on_tool_end":
                yield {
                    "type": "tool_end",
                    "name": name,
                    "label": TOOL_LABELS.get(name, name),
                    "preview": _tool_output_preview(
                        (event.get("data") or {}).get("output")
                    ),
                }
            elif kind == "on_chat_model_stream":
                # 只转发汇总节点的字，专家子图内部的中间输出不要重复推给前端
                meta = event.get("metadata") or {}
                if meta.get("langgraph_node") != "aggregator":
                    continue
                text = _chunk_text((event.get("data") or {}).get("chunk"))
                if text:
                    yield {"type": "token", "content": text}

        yield {"type": "done"}
    except BusinessException as exc:
        yield {"type": "error", "message": exc.message}
    except Exception as exc:
        # 不同厂商的限流异常类名不一样，用类名和文本特征判断，避免绑死某家 SDK
        text = f"{type(exc).__name__} {exc}"
        if "RateLimit" in text or "429" in text or "速率限制" in text:
            yield {"type": "error", "message": "当前请求太频繁，请等几秒再试"}
        elif "Timeout" in text or "timed out" in text:
            yield {"type": "error", "message": "模型响应超时，请稍后重试"}
        else:
            yield {"type": "error", "message": "大模型调用失败，请稍后重试"}
