import sublime
import sublime_plugin
import re
from sys import version

if int(sublime.version()) < 3000:
    from mathsymbols import maths, inverse_maths, synonyms, inverse_synonyms, symbol_by_name, names_by_symbol, get_settings
else:
    from UnicodeMath.mathsymbols import maths, inverse_maths, synonyms, inverse_synonyms, symbol_by_name, names_by_symbol, get_settings

PyV3 = version[0] == "3"

def log(message):
    print(u'UnicodeMath: {0}'.format(message))

def uchr(s):
    return chr(s) if PyV3 else unichr(s)

def get_line_contents(view, location):
    """
    Returns the contents of the line at the given location
    """
    return view.substr(sublime.Region(view.line(location).a, location))

UNICODE_PREFIX_RE = re.compile(r'.*(\\([^\s]+))$')
LIST_PREFIX_RE = re.compile(r'.*(\\\\([^\s\\]+\\[^\s]+))$')
LIST_RE = re.compile(r'^(?P<prefix>[^\s\\]+)\\(?P<list>[^\s]+)$')
UNICODE_LIST_PREFIX_RE = re.compile(r'.*(\\([^\s\\]+)\\([^\s]+))$')
CODE_PREFIX_RE = re.compile(r'.*(u([\da-fA-F]{4}))$')
LONGCODE_PREFIX_RE = re.compile(r'.*(U([\da-fA-F]{8}))')
SYNTAX_RE = re.compile(r'(.*?)/(?P<name>[^/]+)\.tmLanguage')

def get_unicode_prefix(view, location):
    """
    Returns unicode prefix at given location and it's region
    or None if there is no unicode prefix
    """
    cts = get_line_contents(view, location)
    res = LIST_PREFIX_RE.match(cts) or UNICODE_PREFIX_RE.match(cts)
    if res:
        (full_, pref_) = res.groups()
        return (pref_, sublime.Region(location - len(full_), location))
    else:
        return None

def is_unicode_prefix(view, location):
    """
    Returns True if prefix at given location is prefixed with backslash
    """
    cts = get_line_contents(view, location)
    return UNICODE_PREFIX_RE.match(cts) != None

def symbol_by_code(codestr):
    """
    Gets symbol by code string 'uXXXX' or 'UXXXXXXXX'
    """
    m = CODE_PREFIX_RE.match(codestr)
    if m:
        return uchr(int(m.groups()[1], base = 16))
    m = LONGCODE_PREFIX_RE.match(codestr)
    if m:
        u = int(m.groups()[1], base = 16)
        if PyV3 or u < 0xFFFF:
            return uchr(u)
        else:
            a = u / 0x0400 + 0xd7c0
            b = (u & 0x03ff) + 0xdc00
            return unichr(a) + unichr(b)
    return None

def code_by_symbol(sym):
    """
    Get code string in format 'uXXXX' or 'UXXXXXXXX' by symbol
    """
    if len(sym) == 1:
        c = ord(sym[0])
        if c > 0xFFFF:
            return u'U%08X' % c
        else:
            return u'u%04X' % c
    if len(sym) == 2:
        a = ord(sym[0])
        b = ord(sym[1])
        u = (a - 0xd7c0) * 0x0400 + (b - 0xdc00)
        return u'U%08X' % u
    return None

def is_script(s):
    """
    Subscript _... or superscript ^...
    """
    return s.startswith('_') or s.startswith('^')

def get_script(s):
    return (s[0], list(s[1:]))

def get_list_prefix(s):
    # prefix\abc -> (prefix, [a, b, c])
    m = LIST_RE.match(s)
    if not m:
        return (None, None)
    return (m.group('prefix'), list(m.group('list')))

def can_convert(view):
    """
    Determines if there are any regions, where symbol can be converted
    Used not to call command when it will not convert anything, because such call
    modified edit, which lead to call of on_modified recursively
    Some times (is it sublime bug?) on_modified called twice on every change, which makes
    hard to detect whether this on_modified was called as result of previous call of command
    """
    for r in view.sel():
        if r.a == r.b:
            p = get_unicode_prefix(view, r.a)
            if p:
                rep = symbol_by_name(p[0])
                if rep:
                    return True
                (pre, list_chars) = get_list_prefix(p[0])
                if get_settings().get('convert_list', True) and pre is not None:
                    if all([symbol_by_name(pre + ch) for ch in list_chars]):
                        return True
                if get_settings().get('convert_sub_super', True) and is_script(p[0]):
                    (script_char, chars) = get_script(p[0])
                    if all([symbol_by_name(script_char + ch) for ch in chars]):
                        return True
                if get_settings().get('convert_codes', True):
                    rep = symbol_by_code(p[0])
                    if rep:
                        return True
    return False

def syntax_allowed(view):
    """
    Returns whether syntax in view is not in ignore list
    """
    syntax_in_view = SYNTAX_RE.match(view.settings().get('syntax'))
    if syntax_in_view and syntax_in_view.group('name').lower() in get_settings().get('ignore_syntax', []):
        return False
    return True


class UnicodeMathComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # is prefix starts with '\\'
        if not is_unicode_prefix(view, locations[0]):
            return

        # returns completions
        completions = [('\\' + k + '\t' + maths[k], maths[k]) for k in maths.keys() if k.startswith(prefix)]
        completions.extend([('\\' + k + '\t' + maths[synonyms[k]], maths[synonyms[k]]) for k in synonyms.keys() if k.startswith(prefix)])
        return completions

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'unicode_math_syntax_allowed':
            return syntax_allowed(view)
        elif key == 'unicode_math_can_convert':
            return can_convert(view)
        else:
            return False

class UnicodeMathConvert(sublime_plugin.TextCommand):
    def run(self, edit):
        for r in self.view.sel():
            if r.a == r.b:
                p = get_unicode_prefix(self.view, r.a)
                if p:
                    rep = symbol_by_name(p[0])
                    if rep:
                        self.view.replace(edit, p[1], rep)
                        continue
                    (pre, list_chars) = get_list_prefix(p[0])
                    if pre is not None:
                        rep = ''.join([symbol_by_name(pre + ch) for ch in list_chars])
                        self.view.replace(edit, p[1], rep)
                        continue
                    if is_script(p[0]):
                        (script_char, chars) = get_script(p[0])
                        rep = ''.join([symbol_by_name(script_char + ch) for ch in chars])
                        self.view.replace(edit, p[1], rep)
                        continue
                    rep = symbol_by_code(p[0])
                    if rep:
                        self.view.replace(edit, p[1], rep)
                        continue

class UnicodeMathInsertSpace(sublime_plugin.TextCommand):
    def run(self, edit):
        for r in self.view.sel():
            self.view.insert(edit, r.a, " ")

class UnicodeMathSwap(sublime_plugin.TextCommand):
    def run(self, edit):
        for r in self.view.sel():
            upref = get_unicode_prefix(self.view, self.view.word(r).b)
            sym = symbol_by_name(upref[0]) if upref else None
            symc = symbol_by_code(upref[0]) if upref else None
            if upref and (sym or symc):
                self.view.replace(edit, upref[1], sym or symc)
            elif r.b - r.a <= 1:
                u = sublime.Region(r.b - 1, r.b)
                usym = self.view.substr(u)
                names = names_by_symbol(usym)
                if not names:
                    self.view.replace(edit, u, u'\\' + code_by_symbol(usym))
                else:
                    self.view.replace(edit, u, u'\\' + names[0])

class UnicodeMathReplaceInView(sublime_plugin.TextCommand):
    def run(self, edit, replace_with = None):
        if not replace_with:
            return

        for r in self.view.sel():
            self.view.replace(edit, r, replace_with)

class UnicodeMathInsert(sublime_plugin.WindowCommand):
    def run(self):
        self.menu_items = []
        self.symbols = []
        for k, v in maths.items():
            value = v + ' ' + k
            if k in inverse_synonyms:
                value += ' ' + ' '.join(inverse_synonyms[k])
            self.menu_items.append(value)
            self.symbols.append(v)

        self.window.show_quick_panel(self.menu_items, self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        view = self.window.active_view()
        if not view:
            return

        view.run_command('unicode_math_replace_in_view', {
            'replace_with': self.symbols[idx] })
