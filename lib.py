import re
from dataclasses import dataclass

import requests
from requests import Session


@dataclass
class RequestInfo:
    Request_Type: str
    Page: str
    Forms: dict[str, str]
    Headers: dict[str, str]
    Cookies: dict[str, str]
    Params: dict[str, str]
    Files: dict[str, str]


def parse_html(html: str) -> RequestInfo:
    request_type: str = ""
    page: str = ""
    forms: dict[str, str] = {}
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}
    params: dict[str, str] = {}
    files: dict[str, str] = {}
    if "GET-запрос" in html or "Перейдите по" in html:
        request_type = "GET"
    elif "POST-запрос" in html or "Загрузите файлы по" in html:
        request_type = "POST"
    else:
        raise Exception

    if "Загрузите файлы по" in html:
        m = re.search(r'Загрузите файлы по адресу\s*<code>([^<]+)</code>', html)
    elif "GET-запрос" in html or "POST-запрос" in html:
        m = re.search(r'-запрос по адресу\s*<code>([^<]+)</code>', html)
    else:
        m = re.search(r'href=["\']([^"\']+)["\']', html)

    if m:
        page = m.group(1).strip()

    def extract_table(marker: str) -> dict[str, str]:
        result = {}
        pos = html.find(marker)
        if pos != -1:
            table_match = re.search(r'<table[^>]*>(.*?)</table>', html[pos:], re.DOTALL)
            if table_match:
                table_content = table_match.group(1)
                rows = re.findall(r'<tr>\s*<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>\s*</tr>',
                                  table_content, re.DOTALL)
                for k, v in rows:
                    result[k.strip()] = v.strip()
        return result

    if "следующие заголовки" in html:
        headers = extract_table("следующие заголовки")

    if "параметры запроса" in html:
        params = extract_table("параметры запроса")

    if "данные формы" in html:
        forms = extract_table("данные формы")

    if "с указанным содержимым" in html:
        files = extract_table("с указанным содержимым")

    if "cookie" in html.lower():
        cookies = extract_table("cookie")

    return RequestInfo(
        Request_Type=request_type,
        Page=page,
        Forms=forms,
        Headers=headers,
        Cookies=cookies,
        Params=params,
        Files=files)


def send_request(request: RequestInfo, session: Session) -> str:
    full_url = f"http://hw1.alexbers.com{request.Page}"

    cookies = {"user": "083928ed76ec535b7d91ca700acdab55", **request.Cookies}

    if request.Files:
        files_payload = {fname: (fname, content) for fname, content in request.Files.items()}
        resp = session.post(
            full_url,
            headers=request.Headers,
            cookies=cookies,
            params=request.Params,
            files=files_payload,
        )
    elif request.Request_Type == "POST":
        resp = session.post(
            full_url,
            headers=request.Headers,
            cookies=cookies,
            params=request.Params,
            data=request.Forms,
        )
    else:
        resp = session.get(
            full_url,
            headers=request.Headers,
            cookies=cookies,
            params=request.Params,
        )

    return resp.text

session = requests.Session()
first_request = RequestInfo(Request_Type="GET", Page="/", Params={}, Files={}, Cookies={}, Forms={}, Headers={})
response = send_request(first_request, session)

while True:
    try:
        request = parse_html(response)
        print(request)
        response = send_request(request, session)
        print(response)
    except Exception as e:
        print(e)
        print(response)
        break
