UnicodeMath
===========

[![Join the chat at https://gitter.im/mvoidex/UnicodeMath](https://badges.gitter.im/mvoidex/UnicodeMath.svg)](https://gitter.im/mvoidex/UnicodeMath?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Plugin for Sublime for inserting unicode math symbols

Usage
-----

![Input](Images/Input.gif)

Input backslash and name of unicode symbol (for example `\forall`) then insert space and text will be automatically converted to ∀<br>
To insert space use `shift+space`

Emoji
-----

Emoji's names starts with colon (`:`)

![Emoji](Images/Emoji.gif)

Special
---

There are also special way to convert subscripts and superscripts with several symbols, just input several symbols after `\_` or `\^`:
<pre>
S\^1+2k → S¹⁺²ᵏ
S\_1+2k → S₁₊₂ₖ
</pre>
![Script](Images/Script.gif)

You can also convert list of chars with special prefix via `\\prefix\abc`, which will be equivalent to `\prefixa` `\prefixb` and `\prefixc`, for example:
<pre>
\\Bbb\ABCabc → 𝔸𝔹ℂ𝕒𝕓𝕔
</pre>

Hex-code
---

Hex-code of unicode symbol can be also used in one of these formats:
<pre>
\u12ba
\U0001d7be
\U+1F1D1
</pre>

To explicitly convert (or convert back) use commands **UnicodeMath: Convert**, **UnicodeMath: Convert Back**, **UnicodeMath: Convert Back (Code)**

To select symbols from list, use command **UnicodeMath: Insert**

Settings
--------

You can add custom symbols into symbol-table in UnicodeMath settings (Preferences → Package Settings → UnicodeMath → Settings — User or command "Preferences: UnicodeMath Settings — User")

<pre>
	"symbols": {
		"mysymbol": "\u0021",
		"myothersymbol": "\u2080",
		"shortcode": "\\u0021", // code within string
		"longcode": "\\U00000021",
		"pluscode": "\\U+12345",
		"manycodes": "\\U+12345\\u0020",
		"codes-and-text": "Foo\\U+12345"
	}
</pre>

Synonyms for existing symbols can also be set:

<pre>
	"synonyms": {
		"mys": "mysymbol"
	}
</pre>

Now `\mys` will insert the same symbol as `\mysymbol`.

Disable plugin for specific syntaxes (most common and default is 'latex'):

<pre>
	"ignore_syntax": ["latex"]
</pre>

Enable (default) or disable converting hex-codes:

<pre>
	"convert_codes": true
</pre>

Enable (default) or disable converting multichar sub- and superscripts:

<pre>
	"convert_sub_super": true
</pre>

Enable (default) or disable converting list of chars with prefix:

<pre>
	"convert_list": true
</pre>

Font settings
---

I prefer using Lucida Sans Unicode, it contains many unicode symbols.

<pre>
	"font_face": "Lucida Sans Unicode"
</pre>

I also recommend to set `directwrite` font option on Windows to allow font-substitution for unknown unicode symbols

<pre>
	"font_options": ["directwrite"]
</pre>

Symbols table
---

You can see all predefined [emoji](emoji.md), [symbols and synonyms](table.md)
