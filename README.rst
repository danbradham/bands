.. image:: https://img.shields.io/github/license/danbradham/bands.svg?style=flat-square
    :target: https://github.com/danbradham/bands/blob/master/LICENSE
    :alt: License

.. image:: https://img.shields.io/travis/danbradham/bands.svg?style=flat-square
    :target: https://travis-ci.org/danbradham/bands
    :alt: Travis

=====
bands
=====
Another python messaging library

There are ton of python message passing / signal dispatching libraries out
there. Blinker, pysignal, dispatch, pydispatcher, louie, the list goes on and
on. All of these libraries are fine. This library is okay too.

Features
========

- bound and unbound Channels
- Pluggable Dispatchers
- Bands - groups of Channels with their own dispatcher

Working with an unbound Channel
===============================

.. code-block:: console

    >>> import bands

    >>> def on_alert(message):
    ...    return message.upper()

    >>> alert = bands.channel('alert')
    >>> alert.connect(on_alert)
    >>> alert.send('alert!!')
    ['ALERT!!']

Alternatively you can send your message via `bands.send`...

.. code-block:: console

    >>> bands.send('alert', 'ALERT!!')
    ['ALERT!!']

The send method forwards `*args` and `**kwargs` to all of the Channel's
receivers.

Working with bound Channel's
============================
A `Channel` is *bound* when it's `parent` attribute is set. If you use
`bands.channel` as a class attribute, each instance of your class will have
it's own bound `Channel`. This is very similar to the way bound methods in
python work, except with bound Channels you're gauranteed to get the same
bound Channel instance everytime you access it.

.. code-block:: console

    >>> import bands

    >>> class Component(object):
    ...     started = bands.channel('started')
    ...     def __init__(self, name):
    ...         self.name = name
    ...         self.started.connect(self.on_started)
    ...     def on_started(self):
    ...         return self.name + '.on_started'

    >>> Component.started  # doctest:+ELLIPSIS
    <unbound Channel at 0x...>(identifier='started')
    >>> c1 = Component('one')
    >>> c1.started  # doctest:+ELLIPSIS
    <bound Channel at 0x...>(identifier='started')
    >>> c2 = Component('two')
    >>> c2.started  # doctest:+ELLIPSIS
    <bound Channel at 0x...>(identifier='started')
    >>> c1.started.send()
    ['one.on_started']
    >>> c2.started.send()
    ['two.on_started']
    >>> Component.started.send()
    ['one.on_started', 'two.on_started']
    >>> bands.send('started')
    ['one.on_started', 'two.on_started']

From the above example, we can see that each bound Channel has it's own
subscribers. Additionally, if you call send on the unbound Channel, all bound
channel receivers will also be notified. We can also use bands.send to send
messages by identifier string.


Working with a Band
===================
A `Band` is a group of channels with a `Dispatcher` used to actually execute a
Channel's receivers. Messages sent to one `Band` will not reach another
`Band`'s Channels or receivers.

The api functions, `bands.channel` and `bands.send`, delegate their calls to
the active band. The active band defaults to the default Band accessible via
the DEFAULT_BAND constant. You can set the active band with `bands.use_band`,
and get the active band with `bands.get_band`. It may be wise to have a Band
per application or library.

.. code-block:: console

    >>> import bands
    >>> my_band = bands.Band()
    >>> chan = my_band.channel('one')

You can also provide your own Dispatcher to my_band. Here is an example of a
LoggingDispatcher.

.. code-block:: console

    >>> import bands
    >>> import logging

    >>> class LoggingDispatcher(bands.Dispatcher):
    ...     def __init__(self, name):
    ...         self.log = logging.getLogger(name)
    ...     def before_dispatch(self, ctx):
    ...         self.log.debug('Sending %s' % ctx.identifier)

    >>> my_band = bands.Band(LoggingDispatcher('my_band'))

The above LoggingDispatcher will log a debug message before every message is
dispatched to a channels receivers.


Installation
============

.. code-block:: console

    > pip install bands
