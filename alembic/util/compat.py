import collections
import importlib.machinery
import importlib.util
import inspect
import io
import sys

py3k = sys.version_info.major >= 3


ArgSpec = collections.namedtuple(
    "ArgSpec", ["args", "varargs", "keywords", "defaults"]
)


def inspect_getargspec(func):
    """getargspec based on fully vendored getfullargspec from Python 3.3."""

    if inspect.ismethod(func):
        func = func.__func__
    if not inspect.isfunction(func):
        raise TypeError("{!r} is not a Python function".format(func))

    co = func.__code__
    if not inspect.iscode(co):
        raise TypeError("{!r} is not a code object".format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])

    nargs += nkwargs
    varargs = None
    if co.co_flags & inspect.CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & inspect.CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]

    return ArgSpec(args, varargs, varkw, func.__defaults__)


if py3k:
    import builtins as compat_builtins

    def callable(fn):  # noqa
        return hasattr(fn, "__call__")

    def u(s):
        return s

    def ue(s):
        return s


if py3k:

    def _formatannotation(annotation, base_module=None):
        """vendored from python 3.7"""

        if getattr(annotation, "__module__", None) == "typing":
            return repr(annotation).replace("typing.", "")
        if isinstance(annotation, type):
            if annotation.__module__ in ("builtins", base_module):
                return annotation.__qualname__
            return annotation.__module__ + "." + annotation.__qualname__
        return repr(annotation)

    def inspect_formatargspec(
        args,
        varargs=None,
        varkw=None,
        defaults=None,
        kwonlyargs=(),
        kwonlydefaults={},
        annotations={},
        formatarg=str,
        formatvarargs=lambda name: "*" + name,
        formatvarkw=lambda name: "**" + name,
        formatvalue=lambda value: "=" + repr(value),
        formatreturns=lambda text: " -> " + text,
        formatannotation=_formatannotation,
    ):
        """Copy formatargspec from python 3.7 standard library.

        Python 3 has deprecated formatargspec and requested that Signature
        be used instead, however this requires a full reimplementation
        of formatargspec() in terms of creating Parameter objects and such.
        Instead of introducing all the object-creation overhead and having
        to reinvent from scratch, just copy their compatibility routine.

        """

        def formatargandannotation(arg):
            result = formatarg(arg)
            if arg in annotations:
                result += ": " + formatannotation(annotations[arg])
            return result

        specs = []
        if defaults:
            firstdefault = len(args) - len(defaults)
        for i, arg in enumerate(args):
            spec = formatargandannotation(arg)
            if defaults and i >= firstdefault:
                spec = spec + formatvalue(defaults[i - firstdefault])
            specs.append(spec)
        if varargs is not None:
            specs.append(formatvarargs(formatargandannotation(varargs)))
        else:
            if kwonlyargs:
                specs.append("*")
        if kwonlyargs:
            for kwonlyarg in kwonlyargs:
                spec = formatargandannotation(kwonlyarg)
                if kwonlydefaults and kwonlyarg in kwonlydefaults:
                    spec += formatvalue(kwonlydefaults[kwonlyarg])
                specs.append(spec)
        if varkw is not None:
            specs.append(formatvarkw(formatargandannotation(varkw)))
        result = "(" + ", ".join(specs) + ")"
        if "return" in annotations:
            result += formatreturns(formatannotation(annotations["return"]))
        return result


def load_module_py(module_id, path):
    spec = importlib.util.spec_from_file_location(module_id, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module_pyc(module_id, path):
    spec = importlib.util.spec_from_file_location(module_id, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_pep3147():
    return True


try:
    exec_ = getattr(compat_builtins, "exec")
except AttributeError:
    # Python 2
    def exec_(func_text, globals_, lcl):
        exec("exec func_text in globals_, lcl")


################################################
# cross-compatible metaclass implementation
# Copyright (c) 2010-2012 Benjamin Peterson


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("%sBase" % meta.__name__, (base,), {})


################################################

if py3k:

    def raise_(
        exception, with_traceback=None, replace_context=None, from_=False
    ):
        r"""implement "raise" with cause support.

        :param exception: exception to raise
        :param with_traceback: will call exception.with_traceback()
        :param replace_context: an as-yet-unsupported feature.  This is
         an exception object which we are "replacing", e.g., it's our
         "cause" but we don't want it printed.    Basically just what
         ``__suppress_context__`` does but we don't want to suppress
         the enclosing context, if any.  So for now we make it the
         cause.
        :param from\_: the cause.  this actually sets the cause and doesn't
         hope to hide it someday.

        """
        if with_traceback is not None:
            exception = exception.with_traceback(with_traceback)

        if from_ is not False:
            exception.__cause__ = from_
        elif replace_context is not None:
            # no good solution here, we would like to have the exception
            # have only the context of replace_context.__context__ so that the
            # intermediary exception does not change, but we can't figure
            # that out.
            exception.__cause__ = replace_context

        try:
            raise exception
        finally:
            # credit to
            # https://cosmicpercolator.com/2016/01/13/exception-leaks-in-python-2-and-3/
            # as the __traceback__ object creates a cycle
            del exception, replace_context, from_, with_traceback


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self):
        pass
