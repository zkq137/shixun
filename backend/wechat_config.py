"""
微信开放平台扫码登录配置
====================================

使用前需在 https://open.weixin.qq.com 注册开发者账号并创建应用。

一、获取凭据
  1. 登录 微信开放平台 → 管理中心 → 创建网站应用
  2. 获取 AppID 和 AppSecret
  3. 设置授权回调域名（需备案域名，不可用 IP）

二、修改下方 WECHAT_APP_ID / WECHAT_APP_SECRET

三、回调地址
  用户扫码后微信会回调:
    {your_domain}/api/auth/wechat/callback
  此地址必须在开放平台的「授权回调域名」中配置。
"""

# ══════════════════════════════════════════════════
# 请替换为你的真实微信开放平台凭据
# ══════════════════════════════════════════════════
WECHAT_APP_ID = "your_wechat_app_id"
WECHAT_APP_SECRET = "your_wechat_app_secret"

# 微信开放平台接口地址
WECHAT_QR_URL = "https://open.weixin.qq.com/connect/qrconnect"
WECHAT_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"

# 扫码成功后跳转的前端地址
# 如果前端运行在 localhost:5173，使用 http://localhost:5173/login/success
FRONTEND_SUCCESS_URL = "http://localhost:5173/login-success.html"
