# -*- coding: utf-8 -*-
'''
bands
=====
Another python message passing library
'''
from __future__ import absolute_import, print_function
__all__ = [
    'WeakRef',
    'WeakMeth',
    'StrongRef',
    'WeakSet',
    'Context',
    'Dispatcher',
    'Band',
    'Channel',
    'DEFAULT_DISPATCHER',
    'DEFAULT_BAND',
    'ACTIVE_BAND',
    'get_band',
    'use_default_band',
    'use_band',
    'channel',
    'send',
    'is_dispatcher',
    'is_band',
    'is_channel',
    'is_method',
]
__title__ = 'bands'
__author__ = 'Dan Bradham'
__email__ = 'danielbradham@gmail.com'
__url__ = 'https://github.com/danielbradham/bands.git'
__version__ = '0.1.2'
__description__ = 'Another message passing library.'
__license__ = 'MIT'

from collections import defaultdict
import inspect
import weakref


class WeakRef(weakref.ref):
    '''Same as weakref.ref but supports attribute assignment.'''


class WeakMeth(object):
    '''weakref.ref for methods.'''

    def __init__(self, obj, callback=None):
        self.name = obj.__name__
        self.ref = WeakRef(obj.__self__, callback)

    def __call__(self):
        inst = self.ref()
        if inst is None:
            return
        return getattr(inst, self.name)


class StrongRef(object):
    '''Hold a reference to an object.'''

    def __init__(self, obj, callback=None):
        self.name = obj.__name__
        self.obj = obj

    def __call__(self):
        return self.obj


class WeakSet(object):
    '''A weakset implementation that supports methods. The underlying
    data is stored as list so it will remain ordered unlike a true set.
    '''

    def __init__(self, iterator=None):
        self._refs = []
        self._ids = []

        if iterator is not None:
            for item in iterator:
                self.add(item)

    def __len__(self):
        return len(self._ids)

    def __contains__(self, obj):
        return (
            obj in self._ids or
            obj in self._refs or
            self._ref_id(obj) in self._ids
        )

    def __iter__(self):
        for ref in self._refs:
            obj = ref()
            if obj is None:
                continue
            yield obj

    def _ref_id(self, obj):
        if is_method(obj):
            if hasattr(obj, '__func__'):
                return id(obj.__self__), id(obj.__func__)
            return id(obj.__self__), id(obj.__name__)
        else:
            return id(obj)

    def _remove_ref(self, ref):
        ref_id = ref.ref_id
        if ref_id not in self._ids:
            return

        index = self._ids.index(ref_id)
        self._ids.pop(index)
        self._refs.pop(index)

    def add(self, obj, strong=False):
        ref_id = self._ref_id(obj)
        if ref_id in self._ids:
            return

        self._ids.append(ref_id)
        if strong:
            ref = StrongRef(obj)
            ref.ref_id = ref_id
        elif is_method(obj):
            ref = WeakMeth(obj, self._remove_ref)
            ref.ref.ref_id = ref_id
        else:
            ref = WeakRef(obj, self._remove_ref)
            ref.ref_id = ref_id

        self._refs.append(ref)

    def discard(self, obj):
        ref_id = self._ref_id(obj)
        if ref_id not in self._ids:
            return

        index = self._ids.index(ref_id)
        self._ids.pop(index)
        self._refs.pop(index)


class Context(object):
    '''Used by the default Dispatcher implementation. An instance is generated
    by the _dispatch method and passed to before_dispatch and after_dispatch.

    Attributes:
        identifier (str): Channel identifier
        receivers (WeakSet): List of receivers
        args (tuple): Arguments to send to receivers
        kwargs (dict): Kwargs to send to receivers
        results (list): List of results from executing receivers
    '''

    def __init__(self, identifier, receivers, *args, **kwargs):

        self.identifier = identifier
        self.receivers = WeakSet(receivers)
        self.args = args
        self.kwargs = kwargs
        self.results = []


class Dispatcher(object):
    '''Called by a channel to dispatch a message to it's receivers. The
    default dispatcher simply executes the receiver passing along the args and
    kwargs passed to Channel.send.

    The purpose of the Dispatcher class is to allow users to override the
    execution behavior of Channel receivers. For example in a Qt application,
    a user may want to execute the receiver in the main thread, or queue the
    receiver in the main event loop and await the result.

    Subclasses can also provide before_dispatch and after_dispatch methods to
    execute code before and after executing receivers. This is a good
    place to perform logging, broadcast signals across tcp or store
    them in a database. before_dispatch and after_dispatch take a Context
    object as an argument.

    To fully customize a Dispatcher override the _dispatch method. The
    _dispatch method accepts a Channel's identifier, receivers and the
    args and kwargs being sent. The _dispatch method is expected to execute
    all receivers with the provided args and kwargs and return a list of
    results.
    '''

    def _dispatch(self, identifier, receivers, *args, **kwargs):

        ctx = Context(identifier, receivers, args, kwargs)

        if hasattr(self, 'before_dispatch'):
            self.before_dispatch(ctx)

        for receiver in ctx.receivers:
            result = self.dispatch(identifier, receiver, *args, **kwargs)
            ctx.results.append(result)

        if hasattr(self, 'after_dispatch'):
            self.after_dispatch(ctx)

        return ctx.results

    def dispatch(self, identifier, receiver, *args, **kwargs):
        return receiver(*args, **kwargs)


class Band(object):
    '''A collection of Channels. A Channel in one band, will not receiver
    signals from another band. You can override the execution behavior of
    receivers by providing your own subclass of Dispatcher.

    A band will return the same Channel instance for a given identifier
    and parent. However, Band stores only weakrefs to Channels, so if you're
    channel goes out of scope, it will be deleted and any receivers will be
    lost.

    Arguments:
        dispatcher: Dispatcher object with a dispatch method
    '''

    def __init__(self, dispatcher=None):
        self.dispatcher = dispatcher or DEFAULT_DISPATCHER
        self.channels = {}
        self.by_parent = defaultdict(dict)
        self.by_identifier = defaultdict(list)

    def _remove_channel(self, ref):
        '''Cleanup a channel after it's reference dies'''

        identifier, parent_id = ref.key
        if ref.key in self.by_identifier[identifier]:
            self.by_identifier[identifier].remove(ref.key)
        self.by_parent[parent_id].pop(identifier, None)
        self.channels.pop(ref.key, None)

    def send(self, identifier, *args, **kwargs):
        '''Send a message to a channel with the given identifier.'''

        parent = kwargs.pop('parent', None)
        chan = self.channel(identifier, parent)
        return self.dispatch(
            identifier,
            self.get_channel_receivers(chan),
            *args,
            **kwargs
        )

    def dispatch(self, identifier, receivers, *args, **kwargs):
        '''Executes a receiver using this Band's Dispatcher'''
        return self.dispatcher._dispatch(
            identifier,
            receivers,
            *args,
            **kwargs
        )

    def get_channel_receivers(self, chan):
        '''Get all receivers for the provided channel.

        If the channel is bound, yield the bound Channel's receivers
        plus any anonymous receivers connected to an unbound Channel with the
        same identifier.

        If the channel is unbound, yield receivers connected to all unbound
        and bound Channels with the same identifier.
        '''

        if chan.bound:
            yield chan.receivers
            key = chan.identifier, id(None)
            if key in self.channels:
                any_chan = self.channels[(chan.identifier, id(None))]()
                if any_chan:
                    yield any_chan.receivers
        else:
            yield chan.receivers
            for key in self.by_identifier[chan.identifier]:
                other_chan = self.channels[key]()
                if other_chan is chan:
                    continue
                yield other_chan.receivers

    def channel(self, identifier, parent=None):
        '''Get a Channel instance for the provided identifier. If a parent is
        provided return a bound Channel, otherwise return an unbound Channel

        Arguments:
            identifier (str): Identifier of Channel like "started"
            parent (obj): Parent to bind Channel to

        Returns:
            unbound or bound Channel
        '''

        key = (identifier, id(parent))
        if key not in self.channels:
            chan = Channel(identifier, parent, self)
            ref = WeakRef(chan, self._remove_channel)
            ref.key = key
            self.channels[key] = ref
            self.by_parent[id(parent)][identifier] = key
            self.by_identifier[identifier].append(key)
        return self.channels[key]()


class Channel(object):
    '''A Channel used to send messages to connected receivers.

    In literal terms, a Channel is a registry of functions that get called
    in the order they were connected to a Channel instance. Typically, users
    do not create Channel instances manually, they use :func:`channel` factory
    function to create Channels in the active Band or use :meth:`Band.channel`
    to explicitly create a Channel in a Band.

    A Channel can be unbound (anonymous) or bound to an object. When messages
    are sent through an unbound Channel, they are broadcast to unbound and
    bound receivers for the Channel's identifier. When sent through a bound
    Channel, messages are sent to the bound Channel's receivers and receivers
    connected to the unbound Channel with the same identifier.

    Channel objects are also descriptors. When used as a class attribute, the
    Channel will be bound when accessed from an instance. This is similar to
    the way methods work, however, when accessing methods, you get a new
    bound Method instance every time, when accessing channels, you will always
    get the same bound Channel instance.
    '''

    def __init__(self, identifier, parent=None, band=None):
        self.identifier = identifier
        if parent:
            self.parent = weakref.proxy(parent)
        else:
            self.parent = parent
        self.band = band or get_band()
        self.receivers = WeakSet()

    def __get__(self, obj, type):
        if obj is None:
            return self

        chan = self.band.channel(self.identifier, obj)

        # Bind this descriptor to the class instance
        for name, member in inspect.getmembers(type):
            if member is self:
                setattr(obj, name, chan)

        return chan

    def __repr__(self):
        return '<{} {} at 0x{}>(identifier={!r})'.format(
            ('unbound', 'bound')[self.bound],
            self.__class__.__name__,
            id(self),
            self.identifier
        )

    def get_receivers(self):
        for receivers in self.band.get_channel_receivers(self):
            for receiver in receivers:
                yield receiver

    @property
    def bound(self):
        return self.parent is not None

    def send(self, *args, **kwargs):
        return self.band.dispatch(
            self.identifier,
            self.get_receivers(),
            *args, **kwargs
        )

    def connect(self, obj, strong=False):
        self.receivers.add(obj, strong)

    def disconnect(self, obj):
        self.receivers.discard(obj)


DEFAULT_DISPATCHER = Dispatcher()
DEFAULT_BAND = Band()
ACTIVE_BAND = DEFAULT_BAND


def get_band():
    '''Get the currently active Band'''

    return ACTIVE_BAND


def use_default_band():
    '''Set the active band to the default band'''

    global ACTIVE_BAND
    ACTIVE_BAND = DEFAULT_BAND


def use_band(band):
    '''Set the active band to the provided band'''

    global ACTIVE_BAND
    ACTIVE_BAND = band


def channel(identifier, parent=None, band=None):
    '''Get a Channel instance for the provided identifier in the active band.
    If a parent is provided return a bound Channel, otherwise return an
    unbound Channel.

    Arguments:
        identifier (str): Identifier of Channel like "started"
        parent (obj): Parent to bind Channel to

    Returns:
        unbound or bound Channel
    '''

    band = band or ACTIVE_BAND
    return band.channel(identifier, parent)


def send(identifier, *args, **kwargs):
    '''Send a message to a Channel with the given identifier and parent in
    the active band. If no parent is provided, broadcasts *args and **kwargs
    to all unbound and bound receivers for identifier.

    Arguments:
        identifier (str): Identifier of Channel like "started"
        parent (obj): Parent of Channel to send to

    Returns:
        list of results
    '''

    band = kwargs.pop('band', ACTIVE_BAND)
    return band.send(identifier, *args, **kwargs)


def is_dispatcher(obj):
    return isinstance(obj, Dispatcher)


def is_band(obj):
    return isinstance(obj, Band)


def is_channel(obj):
    return isinstance(obj, Channel)


def is_method(obj):
    return hasattr(obj, '__call__') and hasattr(obj, '__self__')
