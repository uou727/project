import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR
from app.dependence.auth import get_current_user
from app.models.user import User
from app.schemas.file import FileResponse

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/upload")
def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """文件上传的接口"""
    if not file.filename:
        raise BusinessException(message="文件名不能为空")

    # 原始的文件名   用户头像.jpg
    original_name = os.path.basename(file.filename)
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessException(message=f"不支持的文件后缀：{ext}")
    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessException(message=f"文件不能超过 {MAX_FILE_SIZE//1024//1024}MB")

    # 设置唯一的文件名称
    disk_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = UPLOAD_DIR / disk_name

    # 流式写文件，边写边统计大小：file.size 不一定有值，靠累计兜住超限
    size = 0
    try:
        with open(save_path, "wb") as f:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise BusinessException(
                        message=f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB"
                    )
                f.write(chunk)
    except Exception:
        # 中断或超限时清掉写了一半的文件，别在 uploads 里留孤儿
        save_path.unlink(missing_ok=True)
        raise

    return Response.success(
        data=FileResponse(
            original_name=original_name,
            disk_name=disk_name,
            size=size,
            url=f"/uploads/{disk_name}",
        )
    )
