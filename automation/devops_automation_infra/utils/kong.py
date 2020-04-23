
class Kong():
    def __init__(self, jwt_token):
        self.token = jwt_token

    @staticmethod
    def create_session(username, password):
        token = "jwt_access"  # login here
        return Kong(token)

    def build_url(self, route):
        # TODO: is something like this enough? like just prepending something to before the route? or do we need more flexible formatting?
        domain = "kong.tls.ai" #or whtaever else you need to put here
        url = f"http://{domain}{route}"
        return url

    def get(self, route, params):
        formatted_url = self.build_url(route)

    def post(self, url, params):
        pass

    def put(self, url, params):
        pass




