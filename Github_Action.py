# SPDX-License-Identifier: GPL-3.0-or-later

"""
euserv 自动续期脚本
功能:
* 使用本地 ddddocr 自动识别验证码
* 发送通知到 Telegram
* 增加登录失败重试机制
* 日志信息格式化
"""
import os
import re
import json
import time
import io
import requests
from bs4 import BeautifulSoup

# 账户信息：用户名和密码
USERNAME = os.getenv('EUSERV_USERNAME')  # 填写用户名或邮箱
PASSWORD = os.getenv('EUSERV_PASSWORD')  # 填写密码

# Mailparser 配置
MAILPARSER_DOWNLOAD_URL_ID = os.getenv('MAILPARSER_DOWNLOAD_URL_ID')
MAILPARSER_DOWNLOAD_BASE_URL = "https://files.mailparser.io/d/"

# Telegram Bot 推送配置
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_USER_ID = os.getenv('TG_USER_ID')
TG_API_HOST = "https://api.telegram.org"

# 代理设置（如果需要）
PROXIES = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}

# 最大登录重试次数
LOGIN_MAX_RETRY_COUNT = 5

# 接收 PIN 的等待时间，单位为秒
WAITING_TIME_OF_PIN = 15

# 登录验证码图片保存目录，GitHub Action 会上传该目录下的图片 artifact
CAPTCHA_IMAGE_SAVE_DIR = os.getenv("CAPTCHA_IMAGE_SAVE_DIR", "captcha_images")

user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/95.0.4638.69 Safari/537.36"
)
desp = ""  # 日志信息
_DDDDOCR_INSTANCE = None

def log(info: str):
    emoji_map = {
        "正在续费": "🔄",
        "检测到": "🔍",
        "ServerID": "🔗",
        "无需更新": "✅",
        "续订错误": "⚠️",
        "已成功续订": "🎉",
        "所有工作完成": "🏁",
        "登陆失败": "❗",
        "验证通过": "✔️",
        "验证失败": "❌",
        "验证码是": "🔢",
        "登录尝试": "🔑",
        "[MailParser]": "📧",
        "[Captcha Solver]": "🧩",
        "[AutoEUServerless]": "🌐",
    }
    # 对每个关键字进行检查，并在找到时添加 emoji
    for key, emoji in emoji_map.items():
        if key in info:
            info = emoji + " " + info
            break

    print(info)
    global desp
    desp += info + "\n\n"


# 登录重试装饰器
def login_retry(*args, **kwargs):
    def wrapper(func):
        def inner(username, password):
            max_retry = kwargs.get("max_retry")
            # 默认重试 3 次
            if not max_retry:
                max_retry = 3

            last_sess_id = "-1"
            last_session = None
            for number in range(1, max_retry + 1):
                if number > 1:
                    log("[AutoEUServerless] 登录尝试第 {} 次".format(number))
                last_sess_id, last_session = func(username, password)
                if last_sess_id != "-1":
                    return last_sess_id, last_session
            return last_sess_id, last_session
        return inner
    return wrapper

# 规范化本地 OCR 返回的验证码文本
def normalize_captcha_code(raw_text: str) -> str:
    text = raw_text.strip()
    text = text.replace(" ", "").replace("\n", "").replace("\t", "")
    text = text.replace("=", "").replace("×", "x").replace("—", "-")
    text = re.sub(r"[^0-9A-Za-z+\-*xX]", "", text)
    if not text:
        return ""

    expression = re.fullmatch(r"(\d+)([+\-*xX])(\d+)", text)
    if expression:
        left = int(expression.group(1))
        operator = expression.group(2)
        right = int(expression.group(3))
        if operator == "+":
            return str(left + right)
        if operator == "-":
            return str(left - right)
        return str(left * right)

    if re.fullmatch(r"[0-9A-Za-z]{6}", text):
        return text
    return ""

# 保存登录验证码原图，方便在 GitHub Action artifact 中查看
def save_captcha_image(image_content: bytes, source: str) -> str:
    if not image_content:
        return ""

    try:
        os.makedirs(CAPTCHA_IMAGE_SAVE_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        millisecond = int(time.time() * 1000) % 1000
        source_part = "_{}".format(source) if source else ""
        filename = "login_captcha{}_{}_{:03d}.png".format(
            source_part, timestamp, millisecond
        )
        path = os.path.join(CAPTCHA_IMAGE_SAVE_DIR, filename)
        with open(path, "wb") as f:
            f.write(image_content)
    except OSError as exc:
        log("[Captcha Solver] 保存登录验证码图片失败: {}".format(exc))
        return ""

    log("[Captcha Solver] 已保存登录验证码图片: {}".format(path))
    return path

# 获取登录验证码原图。只请求一次，确保本地 OCR 识别和日志对应同一张验证码。
def fetch_captcha_image(captcha_image_url: str, session: requests.session) -> bytes:
    response = session.get(captcha_image_url)
    response.raise_for_status()
    return response.content

# 放大图片以提升本地 OCR 对小字符的识别率
def upscale_for_ocr(image, factor=3, border=4):
    from PIL import Image, ImageOps

    resampling = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    bordered = ImageOps.expand(image, border=border, fill=255)
    width, height = bordered.size
    return bordered.resize((width * factor, height * factor), resampling)

# 提取 EUserv 验证码常见的橙色前景
def build_orange_foreground_mask(image):
    from PIL import Image

    hsv = image.convert("HSV")
    mask = Image.new("L", hsv.size, 255)
    source = hsv.load()
    target = mask.load()
    for y in range(hsv.size[1]):
        for x in range(hsv.size[0]):
            hue, saturation, value = source[x, y]
            if 2 <= hue <= 35 and saturation >= 45 and value >= 80:
                target[x, y] = 0
    return mask

# 裁剪二值图前景，避免长干扰线和空白边缘影响本地 OCR
def crop_foreground(image, pad=2):
    pixels = image.load()
    xs = []
    ys = []
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if pixels[x, y] < 128:
                xs.append(x)
                ys.append(y)
    if not xs:
        return image

    left = max(0, min(xs) - pad)
    top = max(0, min(ys) - pad)
    right = min(image.size[0], max(xs) + pad + 1)
    bottom = min(image.size[1], max(ys) + pad + 1)
    return image.crop((left, top, right, bottom))

# 生成适合本地 OCR 的验证码图片变体
def build_local_ocr_image_variants(image):
    from PIL import ImageFilter, ImageOps

    grayscale = ImageOps.autocontrast(image.convert("L"))
    scaled = upscale_for_ocr(grayscale)
    denoised = scaled.filter(ImageFilter.MedianFilter(size=3))

    variants = [scaled, denoised]
    for threshold in (110, 140, 170, 200):
        variants.append(scaled.point(lambda pixel, t=threshold: 255 if pixel > t else 0))
        variants.append(denoised.point(lambda pixel, t=threshold: 255 if pixel > t else 0))

    orange_base = build_orange_foreground_mask(image)
    # 先在原图尺度去除细干扰线，再裁剪放大。这个策略对 EUserv 橙色验证码更稳定。
    orange_opened = orange_base.filter(ImageFilter.MaxFilter(size=5)).filter(
        ImageFilter.MinFilter(size=5)
    )
    for pad in (0, 2, 4, 8, 12):
        cropped = crop_foreground(orange_opened, pad=pad)
        for factor in (1, 2, 3, 4, 5, 6, 8):
            variants.append(upscale_for_ocr(cropped, factor=factor, border=8))

    orange_mask = upscale_for_ocr(orange_base)
    orange_denoised = orange_mask.filter(ImageFilter.MedianFilter(size=3))
    orange_opened = orange_denoised.filter(ImageFilter.MaxFilter(size=3)).filter(
        ImageFilter.MinFilter(size=3)
    )
    orange_closed = orange_denoised.filter(ImageFilter.MinFilter(size=3)).filter(
        ImageFilter.MaxFilter(size=3)
    )
    variants.extend([orange_mask, orange_denoised, orange_opened, orange_closed])
    return variants

# 根据多种 OCR 图片变体的结果挑选最稳定的验证码
def choose_best_local_ocr_candidate(candidates: list) -> str:
    if not candidates:
        return ""

    grouped_counts = {}
    first_candidate = {}
    for code in candidates:
        group_key = code.lower() if re.fullmatch(r"[0-9A-Za-z]{6}", code) else code
        grouped_counts[group_key] = grouped_counts.get(group_key, 0) + 1
        first_candidate.setdefault(group_key, code)

    best_group, count = max(grouped_counts.items(), key=lambda item: item[1])
    if count < 2:
        return ""
    return first_candidate[best_group]

# 本地 ddddocr 验证码解决器
def ddddocr_captcha_solver(captcha_image_content: bytes) -> str:
    try:
        import ddddocr
        from PIL import Image
    except ImportError:
        log("[Captcha Solver] 未安装 ddddocr 或 Pillow，本地 OCR 无法识别验证码。")
        return ""

    try:
        image = Image.open(io.BytesIO(captcha_image_content))
    except Exception as exc:
        log("[Captcha Solver] ddddocr 无法读取验证码图片: {}".format(exc))
        return ""

    global _DDDDOCR_INSTANCE
    if _DDDDOCR_INSTANCE is None:
        try:
            _DDDDOCR_INSTANCE = ddddocr.DdddOcr(show_ad=False)
        except Exception as exc:
            log("[Captcha Solver] ddddocr 初始化失败: {}".format(exc))
            return ""

    candidates = []
    variant_error_count = 0
    variants = [image] + build_local_ocr_image_variants(image)
    for variant in variants:
        try:
            raw_text = _DDDDOCR_INSTANCE.classification(variant.convert("RGB"))
        except Exception:
            variant_error_count += 1
            continue
        code = normalize_captcha_code(raw_text)
        if code:
            candidates.append(code)

    if variant_error_count:
        log("[Captcha Solver] ddddocr 本地 OCR 有 {} 个图片变体识别异常。".format(
            variant_error_count
        ))

    captcha_code = choose_best_local_ocr_candidate(candidates)
    if not captcha_code:
        log("[Captcha Solver] ddddocr 本地 OCR 未识别出稳定结果。")
        return ""

    log("[Captcha Solver] ddddocr 本地 OCR 识别成功。")
    return captcha_code

# 验证码解决器
def captcha_solver(captcha_image_url: str, session: requests.session) -> str:
    captcha_image_content = fetch_captcha_image(captcha_image_url, session)
    save_captcha_image(captcha_image_content, "")

    captcha_code = ddddocr_captcha_solver(captcha_image_content)
    if captcha_code:
        log("[Captcha Solver] 本地 OCR 识别结果: {}".format(captcha_code))
        return captcha_code

    log("[Captcha Solver] 本地 OCR 识别结果为空。")
    return ""

# 从 Mailparser 获取 PIN
def get_pin_from_mailparser(url_id: str) -> str:
    # 从 Mailparser 获取 PIN# 
    response = requests.get(
        f"{MAILPARSER_DOWNLOAD_BASE_URL}{url_id}",
    )
    pin = response.json()[0]["pin"]
    return pin

# 登录函数
@login_retry(max_retry=LOGIN_MAX_RETRY_COUNT)
def login(username: str, password: str) -> (str, requests.session):
    # 登录 EUserv 并获取 session# 
    headers = {"user-agent": user_agent, "origin": "https://www.euserv.com"}
    url = "https://support.euserv.com/index.iphp"
    captcha_image_url = "https://support.euserv.com/securimage_show.php"
    session = requests.Session()

    sess = session.get(url, headers=headers)
    sess_id = re.findall("PHPSESSID=(\\w{10,100});", str(sess.headers))[0]
    session.get("https://support.euserv.com/pic/logo_small.png", headers=headers)

    login_data = {
        "email": username,
        "password": password,
        "form_selected_language": "en",
        "Submit": "Login",
        "subaction": "login",
        "sess_id": sess_id,
    }
    f = session.post(url, headers=headers, data=login_data)
    f.raise_for_status()

    if "Hello" not in f.text and "Confirm or change your customer data here" not in f.text:
        if "To finish the login process please solve the following captcha." not in f.text:
            return "-1", session
        else:
            log("[Captcha Solver] 正在进行验证码识别...")
            captcha_code = captcha_solver(captcha_image_url, session)
            if not captcha_code:
                log("[Captcha Solver] 验证码识别无结果，跳过本次验证码提交。")
                return "-1", session
            log("[Captcha Solver] 识别的验证码是: {}".format(captcha_code))

            f2 = session.post(
                url,
                headers=headers,
                data={
                    "subaction": "login",
                    "sess_id": sess_id,
                    "captcha_code": captcha_code,
                },
            )
            if "To finish the login process please solve the following captcha." not in f2.text:
                log("[Captcha Solver] 验证通过")
                return sess_id, session
            else:
                log("[Captcha Solver] 验证失败")
                return "-1", session
    else:
        return sess_id, session

# 获取服务器列表
def get_servers(sess_id: str, session: requests.session) -> {}:
    # 获取服务器列表# 
    d = {}
    url = "https://support.euserv.com/index.iphp?sess_id=" + sess_id
    headers = {"user-agent": user_agent, "origin": "https://www.euserv.com"}
    f = session.get(url=url, headers=headers)
    f.raise_for_status()
    soup = BeautifulSoup(f.text, "html.parser")
    for tr in soup.select(
        "#kc2_order_customer_orders_tab_content_1 .kc2_order_table.kc2_content_table tr"
    ):
        server_id = tr.select(".td-z1-sp1-kc")
        if not len(server_id) == 1:
            continue
        flag = (
            True
            if tr.select(".td-z1-sp2-kc .kc2_order_action_container")[0]
            .get_text()
            .find("Contract extension possible from")
            == -1
            else False
        )
        d[server_id[0].get_text()] = flag
    return d

# 续期操作
def renew(
    sess_id: str, session: requests.session, password: str, order_id: str, mailparser_dl_url_id: str
) -> bool:
    # 执行续期操作# 
    url = "https://support.euserv.com/index.iphp"
    headers = {
        "user-agent": user_agent,
        "Host": "support.euserv.com",
        "origin": "https://support.euserv.com",
        "Referer": "https://support.euserv.com/index.iphp",
    }
    data = {
        "Submit": "Extend contract",
        "sess_id": sess_id,
        "ord_no": order_id,
        "subaction": "choose_order",
        "choose_order_subaction": "show_contract_details",
    }
    session.post(url, headers=headers, data=data)

    # 弹出 'Security Check' 窗口，将自动触发 '发送 PIN'。
    session.post(
        url,
        headers=headers,
        data={
            "sess_id": sess_id,
            "subaction": "show_kc2_security_password_dialog",
            "prefix": "kc2_customer_contract_details_extend_contract_",
            "type": "1",
        },
    )

    # 等待邮件解析器解析出 PIN
    time.sleep(WAITING_TIME_OF_PIN)
    pin = get_pin_from_mailparser(mailparser_dl_url_id)
    log(f"[MailParser] PIN: {pin}")

    # 使用 PIN 获取 token
    data = {
        "auth": pin,
        "sess_id": sess_id,
        "subaction": "kc2_security_password_get_token",
        "prefix": "kc2_customer_contract_details_extend_contract_",
        "type": 1,
        "ident": f"kc2_customer_contract_details_extend_contract_{order_id}",
    }
    f = session.post(url, headers=headers, data=data)
    f.raise_for_status()
    if not json.loads(f.text)["rs"] == "success":
        return False
    token = json.loads(f.text)["token"]["value"]
    data = {
        "sess_id": sess_id,
        "ord_id": order_id,
        "subaction": "kc2_customer_contract_details_extend_contract_term",
        "token": token,
    }
    session.post(url, headers=headers, data=data)
    time.sleep(5)
    return True

# 检查续期状态
def check(sess_id: str, session: requests.session):
    # 检查续期状态# 
    print("Checking.......")
    d = get_servers(sess_id, session)
    flag = True
    for key, val in d.items():
        if val:
            flag = False
            log("[AutoEUServerless] ServerID: %s 续期失败!" % key)

    if flag:
        log("[AutoEUServerless] 所有工作完成！尽情享受~")

# 发送 Telegram 通知
def telegram():
    message = (
        "<b>AutoEUServerless 日志</b>\n\n" + desp +
        "\n<b>版权声明：</b>\n"
        "本脚本基于 GPL-3.0 许可协议，版权所有。\n\n"
        
        "<b>致谢：</b>\n"
        "特别感谢 <a href='https://github.com/lw9726/eu_ex'>eu_ex</a> 的贡献和启发, 本项目在此基础整理。\n"
        "开发者：<a href='https://github.com/lw9726/eu_ex'>WizisCool</a>\n"
        "<a href='https://www.nodeseek.com/space/8902#/general'>个人Nodeseek主页</a>\n"
        "<a href='https://dooo.ng'>个人小站Dooo.ng</a>\n\n"
        "<b>支持项目：</b>\n"
        "⭐️ 给我们一个 GitHub Star! ⭐️\n"
        "<a href='https://github.com/WizisCool/AutoEUServerless'>访问 GitHub 项目</a>"
    )

    # 请不要删除本段版权声明, 开发不易, 感谢! 感谢!
    # 请勿二次售卖,出售,开源不易,万分感谢!
    data = {
        "chat_id": TG_USER_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true"
    }
    response = requests.post(
        TG_API_HOST + "/bot" + TG_BOT_TOKEN + "/sendMessage", data=data
    )
    if response.status_code != 200:
        print("Telegram Bot 推送失败")
    else:
        print("Telegram Bot 推送成功")



def main_handler(event, context):
    # 主函数，处理每个账户的续期# 
    if not USERNAME or not PASSWORD:
        log("[AutoEUServerless] 你没有添加任何账户")
        exit(1)
    user_list = USERNAME.strip().split()
    passwd_list = PASSWORD.strip().split()
    mailparser_dl_url_id_list = MAILPARSER_DOWNLOAD_URL_ID.strip().split()
    if len(user_list) != len(passwd_list):
        log("[AutoEUServerless] 用户名和密码数量不匹配!")
        exit(1)
    if len(mailparser_dl_url_id_list) != len(user_list):
        log("[AutoEUServerless] mailparser_dl_url_ids 和用户名的数量不匹配!")
        exit(1)
    for i in range(len(user_list)):
        print("*" * 30)
        log("[AutoEUServerless] 正在续费第 %d 个账号" % (i + 1))
        sessid, s = login(user_list[i], passwd_list[i])
        if sessid == "-1":
            log("[AutoEUServerless] 第 %d 个账号登陆失败，请检查登录信息" % (i + 1))
            continue
        SERVERS = get_servers(sessid, s)
        log("[AutoEUServerless] 检测到第 {} 个账号有 {} 台 VPS，正在尝试续期".format(i + 1, len(SERVERS)))
        for k, v in SERVERS.items():
            if v:
                if not renew(sessid, s, passwd_list[i], k, mailparser_dl_url_id_list[i]):
                    log("[AutoEUServerless] ServerID: %s 续订错误!" % k)
                else:
                    log("[AutoEUServerless] ServerID: %s 已成功续订!" % k)
            else:
                log("[AutoEUServerless] ServerID: %s 无需更新" % k)
        time.sleep(15)
        check(sessid, s)
        time.sleep(5)

    # 发送 Telegram 通知
    if TG_BOT_TOKEN and TG_USER_ID and TG_API_HOST:
        telegram()

    print("*" * 30)

if __name__ == "__main__":
    main_handler(None, None)
