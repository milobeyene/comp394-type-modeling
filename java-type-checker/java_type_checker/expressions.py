# -*- coding: utf-8 -*-

from .types import Type


class Expression(object):
    """
        AST for simple Java expressions. Note that this package deal only with compile-time types;
        this class does not actually _evaluate_ expressions.
        """

    def static_type(self):
        """
            Returns the compile-time type of this expression, i.e. the most specific type that describes
            all the possible values it could take on at runtime. Subclasses must implement this method.
            """
        pass

    def check_types(self):
        """
            Validates the structure of this expression, checking for any logical inconsistencies in the
            child nodes and the operation this expression applies to them.
            """
        pass


class Variable(Expression):
    """ An expression that reads the value of a variable, e.g. `x` in the expression `x + 5`.
        """
    def __init__(self, name, declared_type):
        self.name = name                    #: The name of the variable
        self.declared_type = declared_type  #: The declared type of the variable (Type)

    def static_type(self):
        """
        Returns the compile-time type of this expression, i.e. the most specific type that describes
        all the possible values it could take on at runtime.
        """
        return self.declared_type
    def check_types(self):
        """
        Validates the structure of this expression, checking for any logical inconsistencies in the
        child nodes and the operation this expression applies to them.
        """
        return self.declared_type


class Literal(Expression):
    """ A literal value entered in the code, e.g. `5` in the expression `x + 5`.
        """
    def __init__(self, value, type):
        self.value = value  #: The literal value, as a string
        self.type = type    #: The type of the literal (Type)

    def static_type(self):
        """
        Returns the compile-time type of this expression, i.e. the most specific type that describes
        all the possible values it could take on at runtime.
        """
        return self.type
    def check_types(self):
        """
        Validates the structure of this expression, checking for any logical inconsistencies in the
        child nodes and the operation this expression applies to them.
        """
        return self.type

class NullLiteral(Literal):
    def __init__(self):
        super().__init__("null", Type.null)

    def static_type(self):
        """
        Returns the compile-time type of this expression, i.e. the most specific type that describes
        all the possible values it could take on at runtime.
        """
        return Type.null

class MethodCall(Expression):
    """
        A Java method invocation, i.e. `foo.bar(0, 1, 2)`.
        """
    def __init__(self, receiver, method_name, *args):
        self.receiver = receiver        #: The object whose method we are calling (Expression)
        self.method_name = method_name  #: The name of the method to call (String)
        self.args = args                #: The method arguments (list of Expressions)

    def static_type(self):
        """
        Returns the compile-time type of this expression, i.e. the most specific type that describes
        all the possible values it could take on at runtime.
        """

        return self.receiver.static_type().method_named(self.method_name).return_type

    def check_types(self):
        """
        Validates the structure of this expression, checking for any logical inconsistencies in the
        child nodes and the operation this expression applies to them.
        """
        # Check if primitive
        if self.receiver.static_type() is (Type.int or Type.boolean or Type.double or Type.void):
            raise JavaTypeError(
                 "Type {0} does not have methods".format(
                     self.receiver.static_type().name))

        # Check if method exists
        if not self.receiver.static_type().method_named(self.method_name):
            raise JavaTypeError("{0} has no method named {1}".format(
                self.receiver.static_type().name,
                self.method_name
            ))

        # Check length of arguments
        if len(self.receiver.static_type().method_named(self.method_name).argument_types) != len(self.args):
            raise JavaTypeError(
                "Wrong number of arguments for {0}: expected {1}, got {2}".format(
                    self.receiver.static_type().name + '.' + self.method_name + "()",
                    len(self.receiver.static_type().method_named(self.method_name).argument_types),
                    len(self.args)))

        # Check deep expressions...
        passedArguments = []
        for argument in self.args:
            passedArguments.append(argument.static_type())
        for i in range(0, len(self.args)):
            self.args[i].check_types()
            if passedArguments[i] == self.receiver.static_type().method_named(self.method_name).argument_types[i]:
                pass
            elif self.receiver.static_type().method_named(self.method_name).argument_types[i] in \
                    passedArguments[i].direct_supertypes or passedArguments[i] == Type.null:
                pass
            else:
                raise JavaTypeError("{0} expects arguments of type {1}, but got {2}".format(
                    self.receiver.static_type().name + "." +
                    self.receiver.static_type().method_named(self.method_name).name + "()",
                    names(self.receiver.static_type().method_named(self.method_name).argument_types),
                    names(passedArguments)))


class ConstructorCall(Expression):
    """
        A Java object instantiation, i.e. `new Foo(0, 1, 2)`.
        """
    def __init__(self, instantiated_type, *args):
        self.instantiated_type = instantiated_type  #: The type to instantiate (Type)
        self.args = args                            #: Constructor arguments (list of Expressions)


    def static_type(self):
        """
        Returns the compile-time type of this expression, i.e. the most specific type that describes
        all the possible values it could take on at runtime.
        """
        return self.instantiated_type
    def check_types(self):
        """
        Validates the structure of this expression, checking for any logical inconsistencies in the
        child nodes and the operation this expression applies to them.
        """
        # Check if primitive
        if self.instantiated_type is (Type.int or Type.boolean or Type.double or Type.void):
            raise JavaTypeError(
                "Type {0} is not instantiable".format(
                    self.instantiated_type.name))

        # Check if null
        if self.instantiated_type == Type.null:
            raise JavaTypeError("Type null is not instantiable")

        # Check length of arguments
        if len(self.instantiated_type.constructor.argument_types) != len(self.args):
            raise JavaTypeError(
                "Wrong number of arguments for {0}: expected {1}, got {2}".format(
                    self.instantiated_type.name + " constructor",
                    len(self.instantiated_type.constructor.argument_types),
                    len(self.args)))

        # Check for deep expressions...
        passedArguments = []
        expectedArguments = self.instantiated_type.constructor.argument_types

        for argument in self.args:
            passedArguments.append(argument.static_type())
        for i in range(0, len(self.args)):
            self.args[i].check_types()
            if passedArguments[i] == expectedArguments[i]:
                pass
            elif expectedArguments[i] in passedArguments[i].direct_supertypes:
                pass
            elif passedArguments[i] == Type.null and expectedArguments[i] is not (Type.int or Type.boolean or Type.double
                                                                               or Type.void):
                pass
            else:
                raise JavaTypeError("{0} expects arguments of type {1}, but got {2}".format(
                                self.instantiated_type.name + " constructor",
                                names(expectedArguments),
                                names(passedArguments)))

class JavaTypeError(Exception):
    """ Indicates a compile-time type error in an expression.
        """
    pass


def names(named_things):
    """ Helper for formatting pretty error messages
        """
    return "(" + ", ".join([e.name for e in named_things]) + ")"
