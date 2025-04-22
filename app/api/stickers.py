import io
import zipfile
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Path, Request, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db, get_client_ip
from app.models.sticker import Sticker
from app.schemas.sticker import StickerResponse, StickerUpdate, StickerPagination, UploadResponse, \
    StickerDescriptionUpdate
from app.services.sticker_service import sticker_service

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_sticker(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传表情包"""
    # 检查文件类型
    content_type = file.content_type.lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 读取文件内容
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 处理上传
    result = sticker_service.create_sticker(db, file_content)

    if not result["success"]:
        return UploadResponse(
            success=False,
            message=result["message"]
        )

    # 转换结果
    sticker_dict = result["sticker"]
    sticker = db.query(Sticker).filter(Sticker.id == sticker_dict["id"]).first()

    return UploadResponse(
        success=True,
        message="表情包上传成功",
        sticker=StickerResponse.from_orm(sticker) if sticker else None
    )


@router.get("/", response_model=StickerPagination)
def get_stickers(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(20, ge=1, le=100, description="每页数量"),
        sort_by: str = Query("created_at", description="排序字段"),
        sort_order: str = Query("desc", description="排序方式"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        tags: Optional[List[str]] = Query(None, description="标签过滤")
):
    """获取表情包列表"""
    skip = (page - 1) * size
    ip_address = get_client_ip(request)

    stickers, total = sticker_service.get_stickers_with_user_actions(
        db=db,
        ip_address=ip_address,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        search_query=search,
        tags=tags
    )

    # 计算总页数
    pages = (total + size - 1) // size

    return StickerPagination(
        total=total,
        items=stickers,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/random/", response_model=List[StickerResponse])
def get_random_stickers(
        count: int = Query(1, ge=1, le=10, description="随机表情包数量"),
        db: Session = Depends(get_db)
):
    """获取随机表情包"""
    stickers = sticker_service.get_random_stickers(db, count)
    return [StickerResponse.from_orm(s) for s in stickers]


@router.get("/{sticker_id}", response_model=StickerResponse)
def get_sticker(sticker_id: str = Path(..., description="表情包ID"), db: Session = Depends(get_db)):
    """获取单个表情包"""
    sticker = sticker_service.get_sticker(db, sticker_id)
    if not sticker:
        raise HTTPException(status_code=404, detail="表情包不存在")
    return StickerResponse.from_orm(sticker)


@router.put("/{sticker_id}", response_model=StickerResponse)
def update_sticker(
        sticker_update: StickerUpdate,
        sticker_id: str = Path(..., description="表情包ID"),
        db: Session = Depends(get_db)
):
    """更新表情包信息"""
    updated_sticker = sticker_service.update_sticker(db, sticker_id, sticker_update)
    if not updated_sticker:
        raise HTTPException(status_code=404, detail="表情包不存在")
    return StickerResponse.from_orm(updated_sticker)


@router.post("/{sticker_id}/like")
def like_sticker(
        request: Request,
        sticker_id: str = Path(..., description="表情包ID"),
        db: Session = Depends(get_db)
):
    """对表情包点赞"""
    ip_address = get_client_ip(request)
    result = sticker_service.like_sticker(db, sticker_id, ip_address)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.post("/{sticker_id}/dislike")
def dislike_sticker(
        request: Request,
        sticker_id: str = Path(..., description="表情包ID"),
        db: Session = Depends(get_db)
):
    """对表情包点踩"""
    ip_address = get_client_ip(request)
    result = sticker_service.dislike_sticker(db, sticker_id, ip_address)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.get("/tags/popular/", response_model=List[dict])
def get_popular_tags(
        limit: int = Query(20, ge=1, le=100, description="返回标签数量"),
        db: Session = Depends(get_db)
):
    """获取热门标签"""
    return sticker_service.get_popular_tags(db, limit)


@router.post("/download/batch/")
def download_batch_stickers(
        sticker_ids: List[int],
        db: Session = Depends(get_db)
):
    """批量下载表情包"""
    if not sticker_ids:
        raise HTTPException(status_code=400, detail="请提供要下载的表情包ID列表")

    if len(sticker_ids) > 100:
        raise HTTPException(status_code=400, detail="一次最多下载100个表情包")

    # 获取表情包信息
    stickers = sticker_service.batch_download_stickers(db, sticker_ids)

    if not stickers:
        raise HTTPException(status_code=404, detail="没有找到有效的表情包")

    # 创建内存中的ZIP文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for sticker in stickers:
            # 下载表情包图片
            try:
                import requests
                response = requests.get(sticker.url)
                if response.status_code == 200:
                    # 创建一个有意义的文件名
                    filename = f"{sticker.id}_{sticker.description[:10]}_{sticker.md5[-6:]}.png"
                    zip_file.writestr(filename, response.content)
            except Exception as e:
                print(f"下载表情包 {sticker.id} 时出错: {str(e)}")
                continue

    # 设置ZIP文件指针到开头
    zip_buffer.seek(0)

    # 返回流式响应
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=doro_stickers.zip"}
    )


@router.patch("/{sticker_id}/description")
def update_sticker_description(
        sticker_id: str = Path(..., description="表情包ID"),
        description_update: StickerDescriptionUpdate = Body(...),
        db: Session = Depends(get_db)
):
    """修改表情包的描述"""
    result = sticker_service.update_sticker_description(
        db, sticker_id, description_update.description
    )
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result
