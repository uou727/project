import asyncio
import traceback
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.database import SessionLocal
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest, ReservationResponse


def _normalize_date(value: str) -> str:
    """校验并规范化日期，统一成 YYYY-MM-DD"""
    text = (value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise BusinessException(message="日期格式不正确，请使用 YYYY-MM-DD")


def _normalize_time(value: str, label: str) -> str:
    """校验并规范化时间，统一成 HH:MM，兼容 9:00 / 09:00 / 09:00:00"""
    text = (value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    raise BusinessException(message=f"{label}格式不正确，请使用 HH:MM")


def create_reservation(db: Session, current_user: User, data: ReservationCreateRequest):
    """创建预约记录"""
    # 先统一成 YYYY-MM-DD 和 HH:MM 再比较
    # 否则 "9:00" < "10:00" 按字符串比较会判错（字典序 '9' > '1'）
    date = _normalize_date(data.date)
    start_time = _normalize_time(data.start_time, "开始时间")
    end_time = _normalize_time(data.end_time, "结束时间")

    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    if date < current_date:
        raise BusinessException(message="预约日期不能小于当前的日期")
    if end_time < start_time:
        raise BusinessException(message="预约的结束时间不能小于开始时间")
    if date == current_date and start_time < current_time:
        raise BusinessException(message="预约开始时间不能小于当前的时间")
    lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    if lab.status != 1:
        raise BusinessException(message="实验室已关闭")
    if lab.open_time and start_time < _normalize_time(lab.open_time, "实验室开放时间"):
        raise BusinessException(message="预约时间不能早于实验室的开放时间")
    if lab.close_time and end_time > _normalize_time(lab.close_time, "实验室关闭时间"):
        raise BusinessException(message="预约时间不能晚于实验室的关闭时间")

    # equipment_id 不为空 则表示这次是预约的实验室设备
    if data.equipment_id:
        equipment = (
            db.query(Equipment).filter(Equipment.id == data.equipment_id).first()
        )
        if not equipment:
            raise BusinessException(message="实验室设备不存在")
        if equipment.status != 1:
            raise BusinessException(message="实验室设备正在维修")

    # 实验室或者设备是否是可预约的状态
    query = db.query(Reservation).filter(
        Reservation.lab_id == data.lab_id,
        Reservation.date == date,
        Reservation.status.in_([0, 1]),  # 0表示待审核  1已通过
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if data.equipment_id:
        query = query.filter(
            Reservation.equipment_id == data.equipment_id
        )  # 预约实验室设备
    else:
        query = query.filter(Reservation.equipment_id.is_(None))  # 只预约实验室
    res = query.first()
    if res:
        raise BusinessException(message="该时段已预约")

    reservation_model = Reservation(
        user_id=current_user.id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=date,
        start_time=start_time,
        end_time=end_time,
        remark=data.remark,
        status=0,
    )
    db.add(reservation_model)
    db.commit()


def get_reservation_page_list(
    db: Session,
    current_user: User,
    page: int,
    page_size: int,
    status: int | None = None,
):
    """查询预约的记录"""
    query = db.query(Reservation)
    if current_user.role != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    if status is not None:
        query = query.filter(Reservation.status == status)
    total = query.count()
    items = (
        query.order_by(Reservation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for item in items:
        res = ReservationResponse.model_validate(item)
        res.user_name = item.user.name if item.user else None
        res.lab_name = item.lab.name if item.lab else None
        res.equipment_name = item.equipment.name if item.equipment else None
        res.type = "设备" if item.equipment_id else "实验室"
        result.append(res)
    return PageResponse(list=result, total=total)


def cancel_reservation(db: Session, current_user: User, reservation_id: int):
    """学生取消预约"""
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.user_id != current_user.id:
        raise BusinessException(message="无权限", code=403)
    if item.status != 0:
        raise BusinessException(message="当前状态无法取消")
    item.status = 3
    db.commit()


def audit_reservation(db: Session, reservation_id: int, status: int):
    """管理员审核预约"""
    if status not in [1, 2]:
        raise BusinessException(message="审核状态错误")
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.status != 0:
        raise BusinessException(message="当前状态不支持审核")
    item.status = status
    db.commit()


def expire_pending_reservations():
    """批量取消过期的预约单"""
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        # 交给数据库筛一条 UPDATE，避免把全部待审核记录拉进内存逐条比
        db.query(Reservation).filter(
            Reservation.status == 0,
            or_(
                Reservation.date < today,
                and_(Reservation.date == today, Reservation.end_time <= current_time),
            ),
        ).update({"status": 3}, synchronize_session=False)
        db.commit()
    finally:
        db.close()


async def run_expire_scan():
    """1分钟扫描一次执行业务"""
    while True:
        try:
            expire_pending_reservations()
        except Exception:
            # 单次失败（比如数据库断连）不能让整个后台任务退出
            traceback.print_exc()
        await asyncio.sleep(60)
