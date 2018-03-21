import sublime
import sublime_plugin
import re
from sys import version

if int(sublime.version()) < 3000:
    from mathsymbols import *
else:
    from UnicodeMath.mathsymbols import *

PyV3 = version[0] == "3"


UNICODE_SYMBOL_RE = re.compile(r'(?:\\)(?P<symbol>[^\s\\\.,]+)')
UNICODE_RE = re.compile(r'(?:\\)(?:(?P<symbol>[^\s\\\.,]+)|(?:\\(?P<prefix>[^\s\\\.,]+)\\(?P<chars>[^\s\\\.,]+)))')
UNICODE_SYMBOL_PREFIX_RE = re.compile(UNICODE_SYMBOL_RE.pattern + r'$')
UNICODE_PREFIX_RE = re.compile(UNICODE_RE.pattern + r'$')
SYNTAX_RE = re.compile(r'(.*?)/(?P<name>[^/]+)\.(?:tmLanguage|sublime-syntax)')


def log(message):
    print(u'UnicodeMath: {0}'.format(message))


def get_line_contents(view, location):
    """
    Returns the contents of the line at the given location
    """
    return view.substr(sublime.Region(view.line(location).a, location))


def is_script(s):
    """
    Subscript _... or superscript ^...
    """
    return s.startswith('_') or s.startswith('^')


def get_script(s):
    return (s[0], list(s[1:]))


def enabled(name, default=True):
    return get_settings().get(name, default)


def can_convert(view):
    """
    Determines if there are any regions, where symbol can be converted
    Used not to call command when it will not convert anything, because such call
    modified edit, which lead to call of on_modified recursively
    Some times (is it sublime bug?) on_modified called twice on every change, which makes
    hard to detect whether this on_modified was called as result of previous call of command
    """
    prefix_re = UNICODE_PREFIX_RE if enabled('convert_list') else UNICODE_SYMBOL_PREFIX_RE
    for r in view.sel():
        if r.a == r.b:
            line = get_line_contents(view, r.a)
            m = prefix_re.search(line)
            if m:
                symbol = m.groupdict().get('symbol')
                prefix = m.groupdict().get('prefix')
                chars = m.groupdict().get('chars')

                if symbol is not None:
                    if symbol_by_name(symbol):
                        return True
                    elif enabled('convert_sub_super') and is_script(symbol):
                        script_char, chars = get_script(symbol)
                        if all([symbol_by_name(script_char + ch) for ch in chars]):
                            return True
                    elif enabled('convert_codes'):
                        if symbol_by_code(u'\\' + symbol):
                            return True
                elif prefix is not None:
                    if all([symbol_by_name(prefix + ch) for ch in chars]):
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
        prefix_re = UNICODE_PREFIX_RE if enabled('convert_list') else UNICODE_SYMBOL_PREFIX_RE
        line = get_line_contents(view, locations[0])
        m = prefix_re.search(line)
        if not m:
            return

        symbol = m.groupdict().get('symbol')
        pre = m.groupdict().get('prefix')
        chars = m.groupdict().get('chars')

        # returns completions
        if pre is not None:
            def drop_prefix(pr, s):
                return s[len(pr):]
            pref = '\\\\' + pre + '\\' + ''.join(chars)
            completions = [(pref + drop_prefix(pre, k) + '\t' + maths[k], '\\' + pref + drop_prefix(pre, k)) for k in maths.keys() if k.startswith(pre)]
            completions.extend([(pref + drop_prefix(pre, k) + '\t' + maths[synonyms[k]], '\\' + pref + drop_prefix(pre, k)) for k in synonyms.keys() if k.startswith(pre)])
        else:
            completions = [('\\' + k + '\t' + maths[k], maths[k]) for k in maths.keys() if k.startswith(symbol)]
            completions.extend([('\\' + k + '\t' + maths[synonyms[k]], maths[synonyms[k]]) for k in synonyms.keys() if k.startswith(symbol)])
        return sorted(completions, key=lambda k: k[0])

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'unicode_math_syntax_allowed':
            return syntax_allowed(view)
        elif key == 'unicode_math_can_convert':
            return can_convert(view)
        else:
            return False


class UnicodeMathConvert(sublime_plugin.TextCommand):
    def run(self, edit):
        self.prefix_re = UNICODE_PREFIX_RE if enabled('convert_list') else UNICODE_SYMBOL_PREFIX_RE
        self.search_re = UNICODE_RE if enabled('convert_list') else UNICODE_SYMBOL_RE

        for r in self.view.sel():
            if r.a == r.b:
                self.convert_prefix(edit, r)
            else:
                self.convert_selection(edit, r)

    def convert_prefix(self, edit, r):
        line = get_line_contents(self.view, r.a)
        m = self.prefix_re.search(line)
        if m:
            rep = self.replacement(m)
            if rep is not None:
                self.view.replace(edit, sublime.Region(r.begin() - (m.end() - m.start()), r.begin()), rep)

    def convert_selection(self, edit, r):
        contents = self.view.substr(r)
        replaces = []
        # collect replacements as pairs (region, string to replace with)
        for m in self.search_re.finditer(contents):
            rep = self.replacement(m)
            if rep is not None:
                replaces.append((sublime.Region(r.begin() + m.start(), r.begin() + m.end()), rep))
        # apply all replacements
        offset = 0
        for reg, rep in replaces:
            self.view.replace(edit, sublime.Region(reg.begin() + offset, reg.end() + offset), rep)
            offset += len(rep) - reg.size()

    def replacement(self, m):
        symbol = m.groupdict().get('symbol')
        prefix = m.groupdict().get('prefix')
        chars = m.groupdict().get('chars')

        if symbol is not None:
            rep = symbol_by_name(symbol)
            if rep is None:
                if enabled('convert_sub_super') and is_script(symbol):
                    script_char, chars = get_script(symbol)
                    reps = [symbol_by_name(script_char + ch) for ch in chars]
                    if all(reps):
                        rep = ''.join(reps)
            if rep is None:
                if enabled('convert_codes'):
                    rep = symbol_by_code(u'\\' + symbol)
        elif prefix is not None:
            reps = [symbol_by_name(prefix + ch) for ch in chars]
            if all(reps):
                rep = ''.join(reps)

        return rep


class UnicodeMathConvertBack(sublime_plugin.TextCommand):
    """
    Convert symbols back to either name or code
    """
    def run(self, edit, code=False):
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


class UnicodeMathReplaceInView(sublime_plugin.TextCommand):
    def run(self, edit, replace_with=None, begin=None, end=None):
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
