from bands import channel


class Component(object):

    started = channel('started')
    stopped = channel('stopped')

    def __init__(self, name):
        self.name = name
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)

    def on_started(self):
        return self.name + '.on_started'

    def on_stopped(self):
        return self.name + '.on_stopped'


def test_bound_channel():
    '''Test bound channel'''

    def on_started():
        return 'on_started'

    def on_stopped():
        return 'on_stopped'

    c1 = Component('one')
    c1.started.connect(on_started)
    c1.stopped.connect(on_stopped)
    c2 = Component('two')

    # Class attribute started is an unbound Channel
    assert Component.started is not c1.started
    assert not Component.started.bound
    assert Component.stopped is not c1.stopped
    assert not Component.stopped.bound

    # c1.started is a bound Channel
    # repeated access returns the same bound Channel instance
    assert c1.started is c1.started
    assert c1.started.bound
    assert c1.stopped is c1.stopped
    assert c1.stopped.bound

    # c1.started has two connections
    assert c1.started.send() == ['one.on_started', 'on_started']
    assert c1.stopped.send() == ['one.on_stopped', 'on_stopped']

    # deleted receivers go out of scope, automatically disconnecting them
    del(on_started)
    del(on_stopped)
    assert c1.started.send() == ['one.on_started']
    assert c1.stopped.send() == ['one.on_stopped']

    # Every instance gets their own bound Channel instances
    assert c2.started is not c1.started
    assert c2.stopped is not c1.stopped
    assert c2.started.send() == ['two.on_started']
    assert c2.stopped.send() == ['two.on_stopped']

    # Sending messages through the unbound Channel sends to all
    # bound Channels with the same identifier
    # Also, bound Channel receivers are ordered by when they were instantiated
    # c1 was created before c2 therefore...
    assert Component.started.send() == ['one.on_started', 'two.on_started']
    assert Component.stopped.send() == ['one.on_stopped', 'two.on_stopped']


def test_unbound_channel():
    '''Test unbound channel'''

    def receiver():
        return True

    chan = channel('anon')

    # channel returns the same instance for a given identifier
    assert chan is channel('anon')

    # A channel is unbound by default
    assert not chan.bound

    # A channel starts with no receivers
    assert chan.send() == []

    # Connect a receiver
    chan.connect(receiver)
    assert chan.send() == [True]

    # Connecting twice does not add the same receiver twice
    chan.connect(receiver)
    assert chan.send() == [True]

    # Disconnect a receiver
    chan.disconnect(receiver)
    assert chan.send() == []

    # Reconnect receiver and ensure Band does not hold a reference
    # once it is out of scope / all refs are gone
    chan.connect(receiver)
    assert chan.send() == [True]
    del(receiver)
    assert chan.send() == []


def test_strongref():
    '''Test strong references'''

    weak = lambda: 'weak'
    strong = lambda: 'strong'

    chan = channel('anon')
    chan.connect(weak)
    chan.connect(strong, strong=True)

    assert chan.send() == ['weak', 'strong']

    del(weak)
    del(strong)

    # Our strong receiver is still alive!
    assert chan.send() == ['strong']

    # Make sure disconnecting strong receivers works
    strong = list(chan.receivers)[0]
    chan.disconnect(strong)
    assert chan.send() == []
