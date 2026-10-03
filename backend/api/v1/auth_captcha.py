"""图形验证码接口（可拆卸扩展）。

挂载在 ``/api/v1/auth`` 下，负责 ``GET /auth/captcha``：
返回 PNG 图片，验证码 id 放在 ``X-Captcha-Id`` 响应头里。

把本文件删掉，登录流程依然可用，只是前端拿不到验证码
（``backend.services.captcha`` 的失败计数仍会限制暴力破解）。
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.core.rate_limit import limiter
from backend.services import captcha as captcha_service

router = APIRouter()


@router.get("/captcha")
@limiter.limit("30/minute")
async def get_captcha(request: Request) -> Response:
    """获取图形验证码。

    验证码渲染器是可拆卸零件；被摘掉时这里返回 503（而不是 500），
    前端会直接显示 detail。登录流程仍可继续，只是没有验证码。
    """
    try:
        captcha_id, image = captcha_service.create_captcha()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码服务当前不可用，请稍后重试",
        ) from exc

    return Response(
        content=image,
        media_type="image/png",
        headers={
            "X-Captcha-Id": captcha_id,
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
    )
