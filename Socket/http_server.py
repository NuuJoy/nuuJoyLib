

__version__ = (2024, 3, 5, 'alpha')


import http.server
import socketserver
import base64
import json


class Request():
    def __init__(self, headers, rfile):
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

        content = rfile.read(content_length)
        if content_type == 'application/json':
            content = json.loads(content)
        self.Body = content

    def __str__(self):
        output = 'Authorization:'
        if self.Authorization is None:
            output += ' None\n'
        else:
            output += '\n'
            output += f'''    type: {self.Authorization['type']}\n'''
            output += f'''    message: {self.Authorization['token']}\n'''
            for key, val in self.Authorization.items():
                if key not in ('type', 'token'):
                    output += f'''        {key}: {val}\n'''
        output += f'''Content-Type: {self.Headers['Content-Type']}\n'''
        output += f'''Content-Length: {self.Headers['Content-Length']}\n'''
        output += f'''Content: {self.Body}\n'''
        return output


class Simple_Request_Handler(http.server.BaseHTTPRequestHandler):

    def get_request(self):
        return Request(self.headers, self.rfile)

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
        print('Method: GET')
        request = self.get_request()
        print(request)
        self.send_response(
            200, {'status': 'success', 'message': 'GET successfully'}
        )

    def do_POST(self):
        print('Method: POST')
        request = self.get_request()
        print(request)
        self.send_response(
            200, {'status': 'success', 'message': 'POST successfully'}
        )

    def do_PUT(self):
        print('Method: PUT')
        request = self.get_request()
        print(request)
        self.send_response(
            200, {'status': 'success', 'message': 'PUT successfully'}
        )

    def do_DELETE(self):
        print('Method: DELETE')
        request = self.get_request()
        print(request)
        self.send_response(
            200, {'status': 'success', 'message': 'DELETE successfully'}
        )


if __name__ == "__main__":
    with socketserver.TCPServer(
        server_address=('127.0.0.1', 5500),
        RequestHandlerClass=Simple_Request_Handler
    ) as server:
        print('start server...')
        server.serve_forever()
