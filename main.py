import re
import socket
from dataclasses import dataclass
from urllib.parse import urlencode

HOST = "hw1.alexbers.com"
TARGET_IP = socket.gethostbyname(HOST)

@dataclass
class RequestInfo:
    Request_Type: str
    Page: str
    Forms: dict[str, str]
    Headers: dict[str, str]
    Cookies: dict[str, str]
    Params: dict[str, str]
    Files: dict[str, str]

    def to_bytes(self) -> bytes:
        encodedParams = urlencode(self.Params)
        url_path = f"{self.Page}?{encodedParams}" if encodedParams else self.Page

        request = [f"{self.Request_Type} {url_path} HTTP/1.1", "Host: hw1.alexbers.com", ]

        all_cookies = ["user=083928ed76ec535b7d91ca700acdab55"]
        for key, value in self.Cookies.items():
            all_cookies.append(f"{key}={value}")
        request.append(f"Cookie: {'; '.join(all_cookies)}")

        for key, value in self.Headers.items():
            request.append(f"{key}: {value}")
        body = bytearray()
        if self.Files:
            request.append(f"Content-Type: multipart/form-data; boundary=Boundary")

            for filename, content in self.Files.items():
                body.extend(f"--Boundary\r\n".encode("utf-8"))
                body.extend(
                    f'Content-Disposition: form-data; name="{filename}"; filename="{filename}"\r\n'.encode("utf-8"))
                body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
                body.extend(content.encode("utf-8"))
                body.extend(b"\r\n")
            body.extend(f"--Boundary--\r\n".encode("utf-8"))
        elif self.Forms and self.Request_Type == "POST":
            form_str = urlencode(self.Forms)
            body.extend(form_str.encode("utf-8"))
            request.append("Content-Type: application/x-www-form-urlencoded")
        request.append("Connection: close")
        request.append(f"Content-Length: {len(body)}")
        request_bytes = "\r\n".join(request) + "\r\n\r\n"

        return request_bytes.encode() + body


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


def send_request(request: RequestInfo) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TARGET_IP, 80))
    s.sendall(request.to_bytes())
    response = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8")


first_request = RequestInfo(Request_Type="GET", Page="/", Params={}, Files={}, Cookies={}, Forms={}, Headers={})
response = send_request(first_request)

while True:
    try:
        request = parse_html(response)
        print(request)
        response = send_request(request)
        print(response)
    except Exception as e:
        print(e)
        print(response)
        break
