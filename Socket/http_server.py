

__version__ = (2024, 3, 5, 'alpha')


import http.server
import socketserver
import base64
import json


class Request():
    def __init__(self, path, method, headers, rfile):
        self.Path = path
        self.Method = method
        auth = headers['Authorization']
        if auth is None:
            self.Authorization = None
        else:
            authtype, token = auth.split()
            self.Authorization = {
                'type': authtype,
                'token': token
            }
            if authtype == 'Basic':
                user, pswd = base64.b64decode(token).decode().split(':')
                self.Authorization.update({
                    'username': user,
                    'password': pswd
                })
            elif authtype == 'Bearer':
                try:
                    headerb64, payloadb64, signature = token.split('.')
                    header = json.loads(base64.b64decode(headerb64 + '=='))
                    payload = json.loads(base64.b64decode(payloadb64 + '=='))
                    self.Authorization.update({
                        'header': header,
                        'payload': payload,
                        'signature': signature
                    })
                except Exception:
                    pass

        content_type = headers.get_content_type()
        content_length = headers['Content-Length']
        if content_length is None:
            content_length = 0
        else:
            content_length = int(content_length)
        self.Headers = {
            'Content-Type': content_type,
            'Content-Length': content_length
        }

        content = rfile.read(content_length).decode()
        if content_type == 'application/json':
            content = json.loads(content)
        self.Content = content

    def asdict(self):
        return {
            'Path': self.Path,
            'Method': self.Method,
            'Authorization': self.Authorization,
            'Headers': self.Headers,
            'Content': self.Content,
        }

    def __str__(self):
        output = f'Path: {self.Path}\n'
        output += f'Method: {self.Method}\n'
        output += 'Authorization:'
        if self.Authorization is None:
            output += ' None\n'
        else:
            output += '\n'
            output += f'''    type: {self.Authorization['type']}\n'''
            output += f'''    message: {self.Authorization['token']}\n'''
            for key, val in self.Authorization.items():
                if key not in ('type', 'token'):
                    output += f'''        {key}: {val}\n'''
        output += 'Headers:\n'
        output += f'''    Content-Type: {self.Headers['Content-Type']}\n'''
        output += f'''    Content-Length: {self.Headers['Content-Length']}\n'''
        output += f'''Content: {self.Content}\n'''
        return output


class Simple_Request_Handler(http.server.BaseHTTPRequestHandler):

    def get_request(self):
        return Request(self.path, self.command, self.headers, self.rfile)

    def send_response(self, code: int, message: object = None) -> None:
        super().send_response(code)
        if message is None:
            message = b''
        elif isinstance(message, (bytes, str)):
            if isinstance(message, (str,)):
                message = message.encode()
            try:
                json.loads(message)
                content_type = 'application/json'
            except Exception:
                content_type = 'text/html'
        else:
            message = json.dumps(message).encode()
            content_type = 'application/json'
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(message)

    def do_GET(self):
        return self.common_response(self.get_request())

    def do_POST(self):
        return self.common_response(self.get_request())

    def do_PUT(self):
        return self.common_response(self.get_request())

    def do_DELETE(self):
        return self.common_response(self.get_request())

    def common_response(self, request):
        print(request.asdict())
        self.send_response(200, request.asdict())


if __name__ == "__main__":
    with socketserver.TCPServer(
        server_address=('127.0.0.1', 5500),
        RequestHandlerClass=Simple_Request_Handler
    ) as server:
        print('start server...')
        server.serve_forever()
