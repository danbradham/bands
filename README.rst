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

    >>> from bands import channel

    >>> def on_alert(message):
    ...    return message.upper()

    >>> alert = channel('alert')
    >>> alert.connect(on_alert)
    >>> alert.send('alert!!')
    ['ALERT!!']


Working with bound Channel's
============================
A Channel is bound when it's *parent* attribute is set. If you use a channel
as a class attribute, each instance of your class will have it's own bound
Channel. This is very similar to the way bound methods in python work,
except with bound Channels, you're gauranteed to get the same bound Channel
instance everytime you access it.

.. code-block:: console

    >>> import bands
    >>> from bands import channel

    >>> class Component(object):
    ...     started = channel('started')
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
    >>> bands.send('on_started')
    ['one.on_started', 'two.on_started']

From the above example, we can see that each bound Channel has it's own
subscribers. Additionally, if you call send on the unbound Channel, all bound
channel receivers will also be notified. We can also use bands.send to send
messages by identifier string.


Installation
============

.. code-block:: console

    > pip install bands
