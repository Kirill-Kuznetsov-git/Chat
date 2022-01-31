import tornado.ioloop
import tornado.escape
import tornado.options
import tornado.web
import tornado.websocket

import os.path
import logging
import uuid

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/", MainHandler),
                    (r"/chatsocket", ChatSocketHandler),
                    (r"/login", LoginHandler),
                    (r"/logout", LogoutHandler)
                    ]
        settings = dict(
            cookie_secret="bevs54wg5jehvytg45",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            login_url="/login"
        )
        super().__init__(handlers, **settings)


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("index.html", messages=ChatSocketHandler.cache)


class LoginHandler(BaseHandler):
    def get(self):
        self.render("auth.html")

    def post(self):
        login = self.get_body_argument("login")
        self.set_secure_cookie("user", self.get_argument("login"))
        self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect("/login")


class ChatSocketHandler(BaseHandler, tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200

    def open(self):
        self.get_current_user()
        self.get_current_user()
        ChatSocketHandler.waiters.add(self)

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size :]

    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message to %d waiters", len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        chat = {"id": str(uuid.uuid4()), "body": parsed["body"],
                "username": tornado.escape.xhtml_escape(self.get_current_user())}
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat)
        )

        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
