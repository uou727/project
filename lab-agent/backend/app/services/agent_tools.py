import json
from datetime import datetime

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.schemas.reservation import ReservationCreateRequest
from app.services import equipment_service, kb_service, lab_service, reservation_service


def build_tools(db: Session, current_user):
    """知识库检索"""

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
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

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
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)

        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

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
            return json.dumps(
                {"total": page.total, "equipments": rows}, ensure_ascii=False
            )

        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

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
            return json.dumps(
                {
                    "ok": True,
                    "message": "预约已提交，请等待管理员审核",
                    "lab_id": lab_id,
                    "equipment_id": equipment_id,
                    "date": date,
                    "start_time": start_time,
                    "end_time": end_time,
                },
                ensure_ascii=False,
            )
        except BusinessException as exc:
            return json.dumps({"ok": False, "error": exc.message}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def get_today() -> str:
        """获取服务器当前日期，返回格式 YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    return [
        search_lab_docs,
        list_open_labs,
        list_lab_equipments,
        create_lab_reservation,
        get_today,
    ]
