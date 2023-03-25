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
UNICODE_SYMBOL_PREFIX_RE = re.compile(r'(?:\\)(?P<symbol>[^\\]+)$')
UNICODE_PREFIX_RE = re.compile(r'(?:\\)(?:(?P<symbol>[^\\]+)|(?:\\(?P<prefix>[^\s\\\.,]+)\\(?P<chars>[^\s\\\.,]+ ?)))$')
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


def replacement(m, instant=False):
    """
    Returns the conversion for regex match m (with groups 'symbol', 'prefix'
    and 'chars'), None if no conversion is possible.
    If instant=True, restricts to conversions suitable for instant insertion
    """
    symbol = m.groupdict().get('symbol')
    prefix = m.groupdict().get('prefix')
    chars = m.groupdict().get('chars')

    if symbol is not None:
        # Accept explicit symbol names; in instant mode, refuse \^... and \_...
        # (which are left to subs/supers) and ambigous prefixes
        rep = symbol_by_name(symbol)
        if rep and (not instant or (not is_script(symbol) and symbol_by_prefix(symbol, unique=True))):
            return rep

        # Convert unambiguous prefixes
        if enabled('accept_prefixes'):
            rep = symbol_by_prefix(symbol, unique=True)
            if rep:
                return rep

        # Convert subscript and superscripts, but not in instant mode (it would
        # convert immediately at \^ or \_)
        if enabled('convert_sub_super') and is_script(symbol) and (not instant or symbol.endswith(" ")):
            script_char, chars = get_script(symbol.strip())
            reps = [symbol_by_name(script_char + ch) for ch in chars]
            if all(reps):
                return ''.join(reps)

        # Convert Unicode codes
        if enabled('convert_codes'):
            rep = symbol_by_code(u'\\' + symbol)
            if rep:
                return rep

        # In instant mode, accept symbols when followed by an invalid character.
        # For instance, when typing "x" in "\alphax", recognize that "\alpha"
        # was completed, and replace it.
        if instant and symbol is not None and len(symbol) > 1 and not is_script(symbol):
            prefix, suffix = symbol[:-1], symbol[-1]
            rep = symbol_by_name(prefix)
            comp_full = symbol_by_prefix(symbol, unique=False)

            if rep and not comp_full:
                rep = symbol_by_name(prefix)
                if rep:
                    return rep + suffix

    # Substitute prefix combinations (\\prefix\...)
    if prefix is not None and (not instant or chars and chars.endswith(" ")):
        reps = [symbol_by_name(prefix + ch) for ch in chars.strip()]
        if all(reps):
            return ''.join(reps)

def can_convert(view, instant=False):
    """
    Determines if there are any regions, where symbol can be converted
    Used not to call command when it will not convert anything, because such call
    modified edit, which lead to call of on_modified recursively
    Some times (is it sublime bug?) on_modified called twice on every change, which makes
    hard to detect whether this on_modified was called as result of previous call of command
    If instant=True, only allows conversions suitables for automatic insertion
    """
    prefix_re = UNICODE_PREFIX_RE if enabled('convert_list') else UNICODE_SYMBOL_PREFIX_RE
    for r in view.sel():
        if r.a == r.b:
            line = get_line_contents(view, r.a)
            m = prefix_re.search(line)
            if m and replacement(m, instant) is not None:
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
    max_len = max(map(lambda v: len(v), maths.direct.values()))
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
        if not syntax_allowed(view):
            return

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
            completions = [(pref + drop_prefix(pre, k) + '\t' + maths.direct[k], '\\' + pref + drop_prefix(pre, k)) for k in maths.direct.keys() if k.startswith(pre)]
            completions.extend([(pref + drop_prefix(pre, k) + '\t' + maths.direct[synonyms.direct[k]], '\\' + pref + drop_prefix(pre, k)) for k in synonyms.direct.keys() if k.startswith(pre)])
        else:
            completions = [('\\' + k + '\t' + maths.direct[k], maths.direct[k]) for k in maths.direct.keys() if k.startswith(symbol)]
            completions.extend([('\\' + k + '\t' + maths.direct[synonyms.direct[k]], maths.direct[synonyms.direct[k]]) for k in synonyms.direct.keys() if k.startswith(symbol)])
        return sorted(completions, key=lambda k: k[0])

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'unicode_math_syntax_allowed':
            return syntax_allowed(view)
        elif key == 'unicode_math_can_convert':
            return can_convert(view)
        elif key == 'unicode_math_convert_on_space_enabled':
            return enabled('convert_on_space')
        else:
            return False


class UnicodeMathConvert(sublime_plugin.TextCommand):
    def run(self, edit, instant=False):
        self.prefix_re = UNICODE_PREFIX_RE if enabled('convert_list') else UNICODE_SYMBOL_PREFIX_RE
        self.search_re = UNICODE_RE if enabled('convert_list') else UNICODE_SYMBOL_RE

        for r in self.view.sel():
            if r.a == r.b:
                self.convert_prefix(edit, r, instant)
            else:
                self.convert_selection(edit, r, instant)

    def convert_prefix(self, edit, r, instant):
        line = get_line_contents(self.view, r.a)
        m = self.prefix_re.search(line)
        if m:
            rep = replacement(m, instant)
            if rep is not None:
                self.view.replace(edit, sublime.Region(r.begin() - (m.end() - m.start()), r.begin()), rep)

    def convert_selection(self, edit, r, instant):
        contents = self.view.substr(r)
        replaces = []
        # collect replacements as pairs (region, string to replace with)
        for m in self.search_re.finditer(contents):
            rep = replacement(m, instant)
            if rep is not None:
                replaces.append((sublime.Region(r.begin() + m.start(), r.begin() + m.end()), rep))
        # apply all replacements
        offset = 0
        for reg, rep in replaces:
            self.view.replace(edit, sublime.Region(reg.begin() + offset, reg.end() + offset), rep)
            offset += len(rep) - reg.size()

class UnicodeMathConvertInstantly(sublime_plugin.TextChangeListener):
    def __init__(self):
        super().__init__()
        self.running = False

    def on_text_changed(self, changes):
        # Sublime only marks changes as processed once we return. But we run 'unicode_math_convert'
        # which causes text changes; as a result, Sublime will re-invoke this listener before we
        # return, and re-send the same changes since they're not technically "processed" yet. To
        # avoid confusion and infinite loops, disable all the recursive calls.
        if self.running:
            return
        # only convert when adding text (length of old content == 0)
        if enabled('convert_instantly') and any(c.len_utf8 == 0 for c in changes):
            view = sublime.active_window().active_view()
            if view is not None and syntax_allowed(view):
                if can_convert(view, instant=True):
                    self.running = True
                    view.run_command('unicode_math_convert', args={'instant': True})
                    self.running = False

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
        for k, v in maths.direct.items():
            value = v + ' ' + k
            if k in synonyms.inverse:
                value += ' ' + ' '.join(synonyms.inverse[k])
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
