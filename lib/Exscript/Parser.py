import copy
import types
import stdlib
from Exscript import Exscript

class Parser:
    def __init__(self, *args, **kwargs):
        self.input        = ''
        self.input_length = 0
        self.current_char = 0
        self.last_char    = 0
        self.current_line = 1
        self.token_buffer = None
        self.grammar      = []
        self.debug        = 0
        self.variables    = {}
        self.stdlib       = {}
        self.load_stdlib()
        if kwargs.has_key('debug'):
            self.debug = int(kwargs['debug'])


    def define(self, *args, **kwargs):
        self.variables.update(kwargs)


    def load_stdlib(self):
        for modname in stdlib.__dict__['__all__']:
            if self.debug > 0:
                print 'Loading module', modname
            module = __import__('stdlib.' + modname, globals(), locals(), ['stdlib'])
            for funcname in dir(module):
                if funcname.startswith('_'):
                    continue
                efuncname = modname.lower() + '.' + funcname
                if self.debug > 0:
                    print 'Loading function', efuncname
                self.stdlib[efuncname] = module.__dict__[funcname]


    def set_grammar(self, grammar):
        self.grammar.append(grammar)
        self.token_buffer = None


    def restore_grammar(self):
        self.grammar.pop()
        self.token_buffer = None


    def get_line_position_from_char(self, char):
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        return (line_start, line_end)


    def error(self, line, char, type, typename, error):
        if type is None:
            type = Exception
        start, end = self.get_line_position_from_char(char)
        output  = self.input[start:end] + '\n'
        output += (' ' * (char - start)) + '^\n'
        output += '%s in line %s' % (error, line)
        raise type, 'Exscript: ' + typename  + ':\n' + output + '\n'


    def syntax_error(self, error):
        self.error(self.current_line, self.current_char, None, 'Syntax error', error)


    def generic_error(self, sender, typename, error):
        self.error(sender.line, sender.char, None, typename, error)


    def runtime_error(self, sender, error):
        self.generic_error(sender, 'Runtime error', error)


    def exception(self, sender, type, typename, error):
        self.error(sender.line, sender.char, type, typename, error)


    def match(self):
        if self.current_char >= self.input_length:
            self.token_buffer = ('EOF', '')
            return
        for type, regex in self.grammar[-1]:
            match = regex.match(self.input, self.current_char)
            if match is not None:
                self.token_buffer = (type, match.group(0))
                #print "Match:", self.token_buffer
                return
        self.syntax_error('Invalid syntax: %s' % self.input[self.current_char:])


    def next(self):
        self.last_char     = self.current_char + 1
        self.current_char += len(self.token_buffer[1])
        if self.token_buffer[0] == 'newline':
            self.current_line += 1
            #print "Line:", self.current_line
        self.token_buffer = None


    def next_if(self, type, token = None):
        if not self.current_is(type, token):
            return 0
        self.next()
        return 1


    def expect(self, type, token = None):
        (cur_type, cur_token) = self.token()
        if not self.next_if(type, token):
            if token is None:
                error = 'Expected %s but got %s' % (type, cur_type)
            else:
                error = 'Expected "%s" but got "%s"' % (token, cur_token)
            self.syntax_error(error)
        return 1


    def current_is(self, type, token = None):
        if self.token_buffer is None:
            self.match()
        if self.token_buffer[0] != type:
            return 0
        if token is None:
            return 1
        if self.token_buffer[1] == token:
            return 1
        return 0


    def token(self):
        if self.token_buffer is None:
            self.match()
        return self.token_buffer


    def parse(self, string):
        # Re-initialize variables, so that the same parser instance may be used multiple
        # times.
        self.input        = string
        self.input_length = len(string)
        self.current_char = 0
        self.last_char    = 0
        self.current_line = 0
        self.token_buffer = None
        self.grammar      = []
        self.variables    = copy.copy(self.variables)

        # Define the standard library now, in order to prevent it from being overwritten
        # by the user.
        self.define(**self.stdlib)
        compiled = Exscript(self, None, variables = self.variables)
        if self.debug > 3:
            compiled.dump()
        return compiled


    def parse_file(self, filename):
        file   = open(filename)
        string = file.read()
        file.close()
        return self.parse(string)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        filename = 'test.exscript'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        sys.exit(1)
    parser   = Parser()
    compiled = parser.parse_file(filename)
    compiled.dump()