import json
from datetime import date, datetime, timedelta

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.schemas.reservation import ReservationCreateRequest
from app.schemas.study_plan import StudyPlanCreateRequest
from app.services import (
    equipment_service,
    kb_service,
    lab_service,
    reservation_service,
    schedule_service,
    study_plan_service,
)

# 学习规划最多往后看多少天，和 schedule_service 的区间上限保持一致
PLAN_RANGE_DAYS = 7


def _ok(data: dict) -> str:
    """把成功结果序列化成 JSON 字符串返回给模型。"""
    return json.dumps(data, ensure_ascii=False)


def _err(exc: Exception) -> str:
    """工具内部异常统一转成 JSON，让模型看得到原因还能自己重试"""
    message = exc.message if isinstance(exc, BusinessException) else str(exc)
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)


def _parse_date(text: str, field: str) -> date | None:
    """把 YYYY-MM-DD 字符串解析成 date；格式不对时抛业务异常，让模型自己重试。"""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise BusinessException(message=f"{field}格式不正确，请使用 YYYY-MM-DD")


@tool
def get_today() -> str:
    """获取服务器当前日期，返回格式 YYYY-MM-DD。
    用户提到今天、明天、后天、本周时，先调用这个工具换算成具体日期。
    """
    return datetime.now().strftime("%Y-%m-%d")


def build_lab_tools(db: Session, current_user):
    """实验室领域工具：查规则、查实验室与设备、提交预约"""

    @tool
    def search_lab_docs(query: str) -> str:
        """检索实验室知识库文档，输入query检索相关资料
        Args:
            query: 用户检索的查询关键词
        """
        try:
            result = kb_service.search(query) or "没有检索到相关的资料"
            return result
        except Exception as exc:
            return _err(exc)

    @tool
    def list_open_labs(keywords: str = ""):
        """查询所有开放状态的实验室列表，可按名称关键词筛选
        Args:
            keywords: 实验室名称关键词，可选
        """
        try:
            keywords = keywords.strip() or None
            page = lab_service.get_lab_page_list(
                db, page=1, page_size=10, keywords=keywords, status=1
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time,
                }
                for item in page.list
            ]
            return _ok({"total": page.total, "labs": rows})
        except Exception as exc:
            return _err(exc)

    @tool
    def list_lab_equipments(lab_id: int, keywords: str = "") -> str:
        """根据实验室ID，查询该实验室下的设备列表，支持设备名称关键词筛选
        Args:
            lab_id: 实验室ID，必填
            keywords: 设备名称关键词，可选
        """
        try:
            keywords = keywords.strip() or None
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, lab_id=int(lab_id), keywords=keywords
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "lab_id": item.lab_id,
                    "lab_name": item.lab_name,
                    "spec": item.spec,
                    "quantity": item.quantity,
                    "status": item.status,
                }
                for item in page.list
            ]
            return _ok({"total": page.total, "equipments": rows})
        except Exception as exc:
            return _err(exc)

    @tool
    def create_lab_reservation(
        lab_id: int,
        date: str,
        start_time: str,
        end_time: str,
        equipment_id: int | None = None,
        remark: str | None = None,
    ) -> str:
        """创建预约单预约实验室或设备

        Args:
            lab_id: 实验室ID，必填，必须来自 list_open_labs 的查询结果
            date: 预约日期，格式必须是 YYYY-MM-DD，例如 2026-11-03
            start_time: 开始时间，格式必须是 HH:MM，例如 09:00
            end_time: 结束时间，格式必须是 HH:MM，例如 11:00
            equipment_id: 设备ID，可选；不传表示只预约实验室
            remark: 备注，可选
        """
        try:
            data = ReservationCreateRequest(
                lab_id=lab_id,
                equipment_id=equipment_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                remark=remark,
            )
            reservation_service.create_reservation(db, current_user, data)
            return _ok(
                {
                    "ok": True,
                    "message": "预约已提交，请等待管理员审核",
                    "lab_id": lab_id,
                    "equipment_id": equipment_id,
                    "date": date,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )
        except Exception as exc:
            return _err(exc)

    return [
        search_lab_docs,
        list_open_labs,
        list_lab_equipments,
        create_lab_reservation,
        get_today,
    ]


def _schedule_tools(db: Session, current_user):
    """课表查询工具，课表专家和学习规划专家都要用"""

    @tool
    def get_my_schedule(start_date: str = "", end_date: str = "") -> str:
        """查询当前登录学生自己的课表（只能查自己，不能查别人）

        Args:
            start_date: 开始日期，格式 YYYY-MM-DD；不传默认今天
            end_date: 结束日期，格式 YYYY-MM-DD；不传默认开始日期之后 6 天
        """
        try:
            start = _parse_date(start_date, "开始日期") or date.today()
            end = _parse_date(end_date, "结束日期") or (start + timedelta(days=6))
            rows = schedule_service.list_schedules_in_range(
                db, current_user.id, start, end
            )
            return _ok(
                {
                    "total": len(rows),
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                    "schedules": rows,
                    "message": "该区间没有排课" if not rows else "",
                }
            )
        except Exception as exc:
            return _err(exc)

    return [get_my_schedule, get_today]


def build_schedule_tools(db: Session, current_user):
    """课表领域工具"""
    return _schedule_tools(db, current_user)


def build_study_tools(db: Session, current_user):
    """学习规划工具：读已有计划、算空闲时间、保存新计划"""

    @tool
    def get_my_study_plans() -> str:
        """查询当前学生已经保存过的学习计划，用来了解他的学习目标和进度"""
        try:
            rows = study_plan_service.list_recent_plans(db, current_user)
            return _ok(
                {
                    "total": len(rows),
                    "plans": rows,
                    "message": "还没有保存过学习计划" if not rows else "",
                }
            )
        except Exception as exc:
            return _err(exc)

    @tool
    def get_my_free_slots(start_date: str = "", end_date: str = "") -> str:
        """查询当前学生每天没课的时间段，制定学习规划前必须先查这个

        Args:
            start_date: 开始日期，格式 YYYY-MM-DD；不传默认今天
            end_date: 结束日期，格式 YYYY-MM-DD；不传默认开始日期之后 6 天
        """
        try:
            start = _parse_date(start_date, "开始日期") or date.today()
            end = _parse_date(end_date, "结束日期") or (
                start + timedelta(days=PLAN_RANGE_DAYS - 1)
            )
            rows = schedule_service.find_free_slots(db, current_user.id, start, end)
            return _ok(
                {
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                    "days": rows,
                }
            )
        except Exception as exc:
            return _err(exc)

    @tool
    def save_study_plan(content: str) -> str:
        """把用户确认过的学习计划保存到系统里。用户没有明确说“保存/就按这个来”时不要调用。

        Args:
            content: 完整的学习计划内容，包含具体日期和时段安排
        """
        try:
            row = study_plan_service.create_study_plan(
                db, current_user, StudyPlanCreateRequest(content=content)
            )
            return _ok({"ok": True, "message": "学习计划已保存", "plan_id": row.id})
        except Exception as exc:
            return _err(exc)

    return [
        *(_schedule_tools(db, current_user)),
        get_my_study_plans,
        get_my_free_slots,
        save_study_plan,
    ]


def build_all_tools(db: Session, current_user):
    """把三套工具合起来，仅用于调试或单 Agent 场景。

    三套工具都带 get_today，直接拼接会出现同名工具，
    这里按名字去重后再返回。
    """
    collected: dict[str, object] = {}
    for item in [
        *build_lab_tools(db, current_user),
        *build_schedule_tools(db, current_user),
        *build_study_tools(db, current_user),
    ]:
        collected[item.name] = item
    return list(collected.values())
