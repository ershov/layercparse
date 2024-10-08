import regex
from typing import Iterable, Any
from dataclasses import dataclass

from .internal import *
from .common import *
from .ctoken import *
from .statement import *
from .variable import *

reg_define = regex.compile(r"^\#define\s++(?P<name>\w++)\s*+(?P<args>\((?P<args_in>[^)]*+)\))?\s*+(?P<body>.*)$", re_flags)
reg_whole_word = regex.compile(r"[\w\.]++", re_flags)

# The difference from re_token is that # and ## are operators rather than preprocessor directives
re_token_preproc = r'''(?(DEFINE)(?<TOKEN>
    (?> \/\/ (?: [^\\\n] | \\. )*+ \n) |
    (?> \/\* (?: [^*] | \*[^\/] )*+ \*\/ ) |
    (?> " (?> [^\\"] | \\. )* " ) |
    (?> ' (?> [^\\'] | \\. )* ' ) |
    (?> \{ (?&TOKEN)* \} ) |
    (?> \( (?&TOKEN)* \) ) |
    (?> \[ (?&TOKEN)* \] ) |
    (?>\n) |
    [\r\t ]++ |
    (?>\\.) |
    (?> , | ; | \? | : |
        ! | \~ |
        <<= | >>= |
        \#\# | \+\+ | \-\- | \-> | \+\+ | \-\- | << | >> | <= | >= | == | != |
        \&\& | \|\| | \+= | \-= | \*= | /= | %= | \&= | \^= | \|= |
        \# | \. | \+ | \- | \* | \& | / | % | \+ | \- | < | > |
        \& | \^ | \| | = |
        \@ # invalid charachter
    ) |
    \w++
))''' # /nxs;

reg_token_preproc = regex.compile(r"(?&TOKEN)"+re_token_preproc, re_flags)

def is_wellformed(txt: str) -> bool:
    offset = 0
    for match in reg_token_preproc.finditer(txt):
        if match.start() != offset:
            return False
        offset = match.end()
    return offset == len(txt)

@dataclass
class MacroParts:
    name: Token
    args: list[Token] | None = None
    body: Token | None = None
    preComment: Token | None = None
    # postComment: Token | None = None
    is_va_args: bool = False
    is_wellformed: bool = False
    # is_multiple_statements: bool = False

    # TODO: Parse body into a list of tokens. Use special token types for # and ## operators and replacements

    def __post_init__(self):
        self.is_wellformed = is_wellformed(self.body.value) if self.body else True

    def update(self, other: 'MacroParts') -> list[str]:
        errors = []
        if self.name != other.name:
            errors.append(f"macro name mismatch for '{self.name.value}': '{self.name.value}' != '{other.name.value}'")
        if self.args != other.args:
            errors.append(f"macro args mismatch for '{self.name.value}': '{self.args}' != '{other.args}'")
        if self.body != other.body:
            errors.append(f"macro redifinition: '{self.name.value}'")
        if self.preComment is None:
            self.preComment = other.preComment
        return errors

    @staticmethod
    def fromStatement(statement: Statement) -> 'MacroParts | None':
        preComment = None
        for token in statement.tokens:
            if not preComment and token.getKind() == "/":
                preComment = token
                continue
            if token.getKind() in [" ", "/"]:
                continue
            if match := reg_define.match(token.value):
                break
            return None

        is_va_args = False
        offset = token.range[0]
        args = None
        if match["args"]:  # type: ignore # match is not None; match is indexable
            args = list(
            TokenList.xFromMatches(reg_whole_word.finditer(match["args_in"]), # type: ignore # match is not None; match is indexable
                                   offset + match.start("args_in"), kind="w")) # type: ignore # match is not None; match is indexable
            if args and args[-1].value == "...":
                args[-1].value = "__VA_ARGS__"
                is_va_args = True

        body = Token.fromMatch(match, offset, "body") # type: ignore # match is not None; match is indexable
        body.value = clean_text_sz(body.value.replace("\\\n", " \n").strip()) # space to preserve byte offset

        return MacroParts(preComment=preComment, args=args, is_va_args=is_va_args,
            name=Token.fromMatch(match, offset, "name", kind="w"), # type: ignore # match is not None; match is indexable
            body=body) # type: ignore # match is not None; match is indexable

def c_string_escape(txt: str) -> str:
    return txt.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\"", "\\\"")

@dataclass
class Macros:
    macros: dict[str, MacroParts] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def add(self, macro: MacroParts) -> None:
        self.macros[macro.name.value] = macro

    def addFromStatement(self, statement: Statement) -> None:
        if macro := MacroParts.fromStatement(statement):
            self.add(macro)

    def upsert(self, other: MacroParts) -> None:
        if other.name.value in self.macros:
            self.macros[other.name.value].update(other)
        else:
            self.add(other)

    # Macro expansion.
    #  - https://en.wikipedia.org/wiki/C_preprocessor#Order_of_expansion
    #  - https://stackoverflow.com/questions/45375238/c-preprocessor-macro-expansion
    #  - https://gcc.gnu.org/onlinedocs/cpp/Argument-Prescan.html
    def expand(self, txt: str) -> str:
        # TODO: Optimise: compose the result as a list of strings, then join at the end

        if not self.macros:
            return txt

        names_re_a = [
            r"""(?> (?: \# | \/\/ ) (?: [^\\\n] | \\. )*+ \n)""",
            r"""(?> \/\* (?: [^*] | \*[^\/] )*+ \*\/ )""",
            r"""(?> " (?> [^\\"] | \\. )* " )""",
            r"""(?> ' (?> [^\\'] | \\. )* ' )""",
        ]
        kwargs = {}
        if obj_like_names := [k for k, v in self.macros.items() if v.args is None]:
            kwargs["names_obj"] = obj_like_names
            names_re_a.append(r"""(?P<name> \b(?:\L<names_obj>)\b )""")
        if fn_like_names := [k for k, v in self.macros.items() if v.args is not None]:
            kwargs["names_func"] = fn_like_names
            names_re_a.append(r"""(?P<name> \b(?:\L<names_func>)\b )(?P<args>(?P<spc>\s*+)\((?P<list>(?&TOKEN)*+)\))""" + re_token)

        self._names_reg = regex.compile(" | ".join(names_re_a), re_flags, **kwargs)  # type: ignore # **kwargs
        self._in_use: set[str] = set()
        self._in_use_stack: list[str] = []

        self.errors = []
        return self._expand_fragment(txt)

    def _expand_fragment(self, txt: str, base_offset: int = 0) -> str:
        return self._names_reg.sub(
            lambda match: self._expand_fn_like(match, base_offset + base_offset) if match["args"] else \
                          self._expand_obj_like(match, base_offset + base_offset) if match["name"] else \
                          match[0],
            txt)

    def _expand_obj_like(self, match: regex.Match, base_offset: int = 0) -> str:
        name = match["name"]
        if name in self._in_use:
            return match[0]
        if not self.macros[name].body:
            return ""

        self._in_use.add(name)
        self._in_use_stack.append(name)
        # TODO: embed file and line number
        replacement = self._expand_fragment(self.macros[name].body.value, base_offset)  # type: ignore # match is not None
        self._in_use_stack.pop()
        self._in_use.remove(name)

        return replacement

    def _expand_fn_like(self, match: regex.Match, base_offset: int = 0) -> str:
        name = match["name"]
        if name in self._in_use:
            return match[0]
        macro = self.macros[name]
        if not macro.body:
            return ""

        # Parse args
        args_val: list[TokenList] = [TokenList([])]
        for token_arg in TokenList.xFromText(match["list"]):
            # if token_arg.getKind() in ["/", "#"]:
            #     continue
            if token_arg.value == ",":
                if len(args_val) < len(macro.args):  # type: ignore # macro has args
                    args_val.append(TokenList([]))
                    continue
                # Reached the required number of arguments
                if not macro.is_va_args:
                    break
                # if va_args, continue appending to the last list
            args_val[-1].append(token_arg)
        if len(args_val) < len(macro.args):  # type: ignore # macro has args
            self.errors.append(f"error: macro {name}: got only {len(args_val)} arguments, expected {len(macro.args)}")   # type: ignore # macro has args # TODO: better error reporting
            return match[0]

        replacement = macro.body.value  # type: ignore # match is not None

        if macro.args:  # Can be an empty list
            args_dict = {k.value: Token(0, v.range(), "".join(v.strings()).strip()) for k, v in zip(macro.args, args_val)}

            # Calculate expanded arguments
            args_dict_expanded = {k: Token(0, v.range, self._expand_fragment(v.value, base_offset+v.range[0])) \
                    for k, v in args_dict.items()}

            # Replace operators # and ## and arguments
            reg_macro_subst = regex.compile(r"""
                (?P<h> \#\s*+ (?P<n>\w++) ) |
                (?P<hh> (?P<n>\w++)(?>\s*+(\#\#)\s*+(?P<n>\w++))++) |
                (?P<n>\b(?:\L<names>)\b)
            """, re_flags, names=args_dict.keys())

            def _concat_hh(match: regex.Match) -> str:
                return "".join(((args_dict[name].value if name in args_dict else name) for name in match.capturesdict()["n"]))
            def _arg_c_escape(name: str) -> str:
                return '"'+c_string_escape(args_dict[name].value)+'"' if name in args_dict else '""'

            replacement = reg_macro_subst.sub(
                lambda match: _arg_c_escape(match["n"]) if match["h"] else \
                              _concat_hh(match) if match["hh"] else \
                              args_dict_expanded[match["n"]].value,
                replacement)

        # Another round of global replacement
        self._in_use.add(name)
        self._in_use_stack.append(name)
        replacement = self._expand_fragment(replacement, base_offset+match.start())
        self._in_use_stack.pop()
        self._in_use.remove(name)

        return replacement
