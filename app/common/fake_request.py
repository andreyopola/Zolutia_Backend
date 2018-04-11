class FakeRequest(dict):
    def __init__(self, data):
        super().__init__()

        self.json = data
        self.unparsed_arguments = {}

    def __repr__(self):
        return repr(self.json)
