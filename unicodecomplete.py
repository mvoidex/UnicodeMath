import sublime
import sublime_plugin
import re
from sys import version

if int(sublime.version()) < 3000:
    from mathsymbols import *
else:
    from UnicodeMath.mathsymbols import *

PyV3 = version[0] == "3"


def log(message):
    print(u'UnicodeMath: {0}'.format(message))


def get_line_contents(view, location):
    """
    Returns the contents of the line at the given location
    """
    return view.substr(sublime.Region(view.line(location).a, location))

UNICODE_PREFIX_RE = re.compile(r'.*(\\([^\s]*))$')
LIST_PREFIX_RE = re.compile(r'.*(\\\\([^\s\\]+\\[^\s]*))$')
LIST_RE = re.compile(r'^(?P<prefix>[^\s\\]+)\\(?P<list>[^\s]*)$')
UNICODE_LIST_PREFIX_RE = re.compile(r'.*(\\([^\s\\]+)\\([^\s]+))$')
SYNTAX_RE = re.compile(r'(.*?)/(?P<name>[^/]+)\.(?:tmLanguage|sublime-syntax)')


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
    return (UNICODE_PREFIX_RE.match(cts) is not None) or (LIST_PREFIX_RE.match(cts) is not None)


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
                    rep = symbol_by_code(u'\\' + p[0])
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


def find_rev(view, r):
    # Go through all prefixes starting from longest
    # Returns prefix length and its names + possibly code
    # Order:
    #   - name - may not present
    #   - synonyms... - may not presend
    #   - code - always present
    max_len = max(map(lambda v: len(v), maths.values()))
    prefix = get_line_contents(view, r.end())

    for i in reversed(range(1, max_len + 1)):
        cur_pref = prefix[-i:]
        if len(cur_pref) < i:
            continue
        names = list(map(lambda n: u'\\' + n, names_by_symbol(cur_pref)))
        if names or i == 1:  # For prefix 1 (one symbol) there always exists code
            names.append(u''.join([code_by_symbol(c) for c in cur_pref]))
        if names:
            region = sublime.Region(r.end() - i, r.end())
            return (region, names)
    return (r, [])


class UnicodeMathComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        p = get_unicode_prefix(view, locations[0])
        if not p:
            return

        (pre, list_chars) = get_list_prefix(p[0])
        # returns completions
        if pre is not None:
            def drop_prefix(pr, s):
                return s[len(pr):]
            pref = '\\\\' + pre + '\\' + ''.join(list_chars)
            completions = [(pref + drop_prefix(pre, k) + '\t' + maths[k], '\\' + pref + drop_prefix(pre, k)) for k in maths.keys() if k.startswith(pre)]
            completions.extend([(pref + drop_prefix(pre, k) + '\t' + maths[synonyms[k]], '\\' + pref + drop_prefix(pre, k)) for k in synonyms.keys() if k.startswith(pre)])
        else:
            completions = [('\\' + k + '\t' + maths[k], maths[k]) for k in maths.keys() if k.startswith(p[0])]
            completions.extend([('\\' + k + '\t' + maths[synonyms[k]], maths[synonyms[k]]) for k in synonyms.keys() if k.startswith(p[0])])
        return sorted(completions, key = lambda k: k[0])

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'unicode_math_syntax_allowed':
            return syntax_allowed(view)
        elif key == 'unicode_math_can_convert':
            return can_convert(view)
        else:
            return False


class UnicodeMathConvert(sublime_plugin.TextCommand):
    def run(self, edit):
        region=self.view.sel()[0]
        if region.a != region.b:
            s = self.view.substr(region)
            self.view.sel().clear()
            i=0
            while i<len(s):
                if s[i]=='\\':
                    if i<len(s)-1 and s[i+1]=='\\':
                        i=i+2
                        continue
                    j=i+1
                    while j<len(s):
                        if s[j]==' ' or s[j]=='\n' or s[j]=='\\':
                            break
                        j=j+1
                    self.view.sel().add(sublime.Region(region.begin()+j,region.begin()+j))
                    i=j
                else:
                    i=i+1
            self.view.sel().add(sublime.Region(region.end(),region.end()))
        for r in self.view.sel():
            if r.a == r.b:
                p = get_unicode_prefix(self.view, r.a)
                if p:
                    cnt=r.a-region.begin()
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
                    rep = symbol_by_code(u'\\' + p[0])
                    if rep:
                        self.view.replace(edit, p[1], rep)
                        continue
        if region.a != region.b:
            end=(self.view.sel()[-1]).a
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(region.begin(),end))

class UnicodeMathConvertBack(sublime_plugin.TextCommand):
    """
    Convert symbols back to either name or code
    """
    def run(self, edit, code = False):
        if len(self.view.sel()) == 1:
            (region, names) = find_rev(self.view, self.view.sel()[0])
            if code:
                self.view.replace(edit, region, names[-1])
            else:
                if len(names) <= 2:  # name or name + code
                    self.view.replace(edit, region, names[0])
                else:
                    self.region = region
                    self.names = names
                    self.view.window().show_quick_panel(self.names[:-1], self.on_done)
        else:
            for r in self.view.sel():
                (region, names) = find_rev(self.view, r)
                if names:
                    self.view.replace(edit, region, names[-1] if code else names[0])

    def on_done(self, idx):
        if idx == -1:
            return

        self.view.run_command('unicode_math_replace_in_view', {
            'replace_with': self.names[idx],
            'begin': self.region.begin(),
            'end': self.region.end()})


class UnicodeMathInsertSpace(sublime_plugin.TextCommand):
    def run(self, edit):
        for r in self.view.sel():
            self.view.insert(edit, r.a, " ")


class UnicodeMathSwap(sublime_plugin.TextCommand):
    def run(self, edit):
        for r in self.view.sel():
            upref = get_unicode_prefix(self.view, self.view.word(r).b)
            sym = symbol_by_name(upref[0]) if upref else None
            symc = symbol_by_code(u'\\' + upref[0]) if upref else None
            if upref and (sym or symc):
                self.view.replace(edit, upref[1], sym or symc)
            elif r.b - r.a <= 1:
                u = sublime.Region(r.b - 1, r.b)
                usym = self.view.substr(u)
                names = names_by_symbol(usym)
                if not names:
                    self.view.replace(edit, u, code_by_symbol(usym))
                else:
                    self.view.replace(edit, u, u'\\' + names[0])


class UnicodeMathReplaceInView(sublime_plugin.TextCommand):
    def run(self, edit, replace_with = None, begin = None, end = None):
        if not replace_with:
            return

        if begin is not None and end is not None:  # Excplicit region
            self.view.replace(edit, sublime.Region(int(begin), int(end)), replace_with)
        else:
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
            'replace_with': self.symbols[idx]})
