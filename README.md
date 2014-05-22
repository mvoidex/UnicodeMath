UnicodeMath
===========

Plugin for Sublime for inserting unicode math symbols

Usage
-----

Input backslash and name of unicode symbol:
<pre>
\forall
</pre>
then insert space and text will be automatically converted to ∀
To insert space use shift+space

Hex-code of unicode symbol can be also used in one of these formats:
<pre>
\u12ba
\U0001d7be
</pre>

To explicitly convert (or convert back) use command 'UnicodeMath: Swap'

To select symbols from list, use command 'UnicodeMath: Insert'

Settings
--------

You can add custom symbols into symbol-table in UnicodeMath settings (Preferences → Package Settings → UnicodeMath → Settings — User or command "Preferences: UnicodeMath Settings — User")

<pre>
	"symbols": {
		"mysymbol": "\u0021",
		"myothersymbol": "\u2080"
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
