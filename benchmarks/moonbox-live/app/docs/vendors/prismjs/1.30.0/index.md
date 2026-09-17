[Used By](#used-by)
-------------------

Prism is used on several websites, small and large. Some of them are:

[![Smashing Magazine](https://prismjs.com/assets/img/logo-smashing.png)](https://www.smashingmagazine.com/) [![A List Apart](https://prismjs.com/assets/img/logo-ala.png)](https://alistapart.com/) [![Mozilla Developer Network (MDN)](https://prismjs.com/assets/img/logo-mdn.png)](https://developer.mozilla.org/) [![CSS-Tricks](https://prismjs.com/assets/img/logo-css-tricks.png)](https://css-tricks.com/) [![SitePoint](https://prismjs.com/assets/img/logo-sitepoint.png)](https://www.sitepoint.com/) [![Drupal](https://prismjs.com/assets/img/logo-drupal.png)](https://www.drupal.org/) [![React](https://prismjs.com/assets/img/logo-react.png)](https://reactjs.org/) [![Stripe](https://prismjs.com/assets/img/logo-stripe.png)](https://stripe.com/) [![MySQL](https://prismjs.com/assets/img/logo-mysql.png)](https://dev.mysql.com/)

[Examples](#examples)
---------------------

The Prism source, highlighted with Prism (don’t you just love how meta this is?):

This page’s CSS code, highlighted with Prism:

This page’s HTML, highlighted with Prism:

This page’s logo (SVG), highlighted with Prism:

If you’re still not sold, you can [view more examples](https://prismjs.com/examples) or [try it out for yourself](https://prismjs.com/test).

[Full list of features](#full-list-of-features)
-----------------------------------------------

*   **Only 2KB** minified & gzipped (core). Each language definition adds roughly 300-500 bytes.
*   Encourages good author practices. Other highlighters encourage or even force you to use elements that are semantically wrong, like `<pre>` (on its own) or `<script>`. Prism forces you to use the correct element for marking up code: `<code>`. On its own for inline code, or inside a `<pre>` for blocks of code. In addition, the language is defined through the way recommended in the HTML5 draft: through a `language-xxxx` class.
*   The `language-xxxx` class is inherited. This means that if multiple code snippets have the same language, you can just define it once, in one of their common ancestors.
*   Supports **parallelism with Web Workers**, if available. Disabled by default ([why?](https://prismjs.com/faq#why-is-asynchronous-highlighting-disabled-by-default)).
*   Very easy to extend without modifying the code, due to Prism’s [plugin architecture](#plugins). Multiple hooks are scattered throughout the source.
*   Very easy to [define new languages](https://prismjs.com/extending#language-definitions). The only thing you need is a good understanding of regular expressions.
*   All styling is done through CSS, with [sensible class names](https://prismjs.com/faq#how-do-i-know-which-tokens-i-can-style-for) rather than ugly, namespaced, abbreviated nonsense.
*   Wide browser support: Edge, IE11, Firefox, Chrome, Safari, [Opera](https://prismjs.com/faq#this-page-doesnt-work-in-opera), most mobile browsers.
*   Highlights embedded languages (e.g. CSS inside HTML, JavaScript inside HTML).
*   Highlights inline code as well, not just code blocks.
*   It doesn’t force you to use any Prism-specific markup, not even a Prism-specific class name, only standard markup you should be using anyway. So, you can just try it for a while, remove it if you don’t like it and leave no traces behind.
*   Highlight specific lines and/or line ranges (requires [plugin](https://prismjs.com/plugins/line-highlight/)).
*   Show invisible characters like tabs, line breaks etc (requires [plugin](https://prismjs.com/plugins/show-invisibles/)).
*   Autolink URLs and emails, use Markdown links in comments (requires [plugin](https://prismjs.com/plugins/autolinker/)).

[Limitations](#limitations)
---------------------------

*   Any pre-existing HTML in the code will be stripped off. [There are ways around it though](https://prismjs.com/faq#if-pre-existing-html-is-stripped-off-how-can-i-highlight).
*   Regex-based so it \*will\* fail on certain edge cases, which are documented in the [known failures page](https://prismjs.com/known-failures).
*   Some of our themes have problems with certain layouts. Known cases are documented [here](https://prismjs.com/known-failures#themes).
*   No IE 6-10 support. If someone can read code, they are probably in the 95% of the population with a modern browser.

[Basic usage](#basic-usage)
---------------------------

You will need to include the `prism.css` and `prism.js` files you [downloaded](https://prismjs.com/download) in your page. Example:

    <!DOCTYPE html>
    <html>
    <head>
    	...
    	<link href="themes/prism.css" rel="stylesheet" />
    </head>
    <body>
    	...
    	<script src="prism.js"></script>
    </body>
    </html>

Prism does its best to encourage good authoring practices. Therefore, it only works with `<code>` elements, since marking up code without a `<code>` element is semantically invalid. [According to the HTML5 spec](https://www.w3.org/TR/html52/textlevel-semantics.html#the-code-element), the recommended way to define a code language is a `language-xxxx` class, which is what Prism uses. Alternatively, Prism also supports a shorter version: `lang-xxxx`.

The [recommended way to mark up a code block](https://www.w3.org/TR/html5/grouping-content.html#the-pre-element) (both for semantics and for Prism) is a `<pre>` element with a `<code>` element inside, like so:

    <pre><code class="language-css">p { color: red }</code></pre>

If you use that pattern, the `<pre>` will automatically get the `language-xxxx` class (if it doesn’t already have it) and will be styled as a code block.

Inline code snippets are done like this:

    <code class="language-css">p { color: red }</code>

**Note**: You have to escape all `<` and `&` characters inside `<code>` elements (code blocks and inline snippets) with `&lt;` and `&amp;` respectively, or else the browser might interpret them as an HTML tag or [entity](https://developer.mozilla.org/en-US/docs/Glossary/Entity). If you have large portions of HTML code, you can use the [Unescaped Markup plugin](https://prismjs.com/plugins/unescaped-markup/) to work around this.

[Language inheritance](#language-inheritance)
---------------------------------------------

To make things easier however, Prism assumes that the language class is inherited. Therefore, if multiple `<code>` elements have the same language, you can add the `language-xxxx` class on one of their common ancestors. This way, you can also define a document-wide default language, by adding a `language-xxxx` class on the `<body>` or `<html>` element.

If you want to opt-out of highlighting a `<code>` element that inherits its language, you can add the `language-none` class to it. The `none` language can also be inherited to disable highlighting for the element with the class and all of its descendants.

If you want to opt-out of highlighting but still use plugins like [Show Invisibles](https://prismjs.com/plugins/show-invisibles/), use `language-plain` class instead.

[Manual highlighting](#manual-highlighting)
-------------------------------------------

If you want to prevent any elements from being automatically highlighted and instead use the [API](https://prismjs.com/extending#api-documentation), you can set [`Prism.manual`](https://prismjs.com/docs/prism#.manual) to `true` before the `DOMContentLoaded` event is fired. By setting the `data-manual` attribute on the `<script>` element containing Prism core, this will be done automatically. Example:

    <script src="prism.js" data-manual></script>

or

    <script>
    window.Prism = window.Prism || {};
    window.Prism.manual = true;
    </script>
    <script src="prism.js"></script>

[Usage with CDNs](#basic-usage-cdn)
-----------------------------------

In combination with CDNs, we recommend using the [Autoloader plugin](https://prismjs.com/plugins/autoloader) which automatically loads languages when necessary.

The setup of the Autoloader, will look like the following. You can also add your own themes of course.

    <!DOCTYPE html>
    <html>
    <head>
    	...
    	<link href="https:///prismjs@v1.x/themes/prism.css" rel="stylesheet" />
    </head>
    <body>
    	...
    	<script src="https:///prismjs@v1.x/components/prism-core.min.js"></script>
    <script src="https:///prismjs@v1.x/plugins/autoloader/prism-autoloader.min.js"></script>
    </body>
    </html>

Please note that links in the above code sample serve as placeholders. You have to replace them with valid links to the CDN of your choice.

CDNs which provide PrismJS are e.g. [cdnjs](https://cdnjs.com/libraries/prism), [jsDelivr](https://www.jsdelivr.com/package/npm/prismjs), and [UNPKG](https://unpkg.com/browse/prismjs@1/).

[Usage with Webpack, Browserify, & Other Bundlers](#basic-usage-bundlers)
-------------------------------------------------------------------------

If you want to use Prism with a bundler, install Prism with `npm`:

    $ npm install prismjs

You can then `import` into your bundle:

    import Prism from 'prismjs';

To make it easy to configure your Prism instance with only the languages and plugins you need, use the babel plugin, [babel-plugin-prismjs](https://github.com/mAAdhaTTah/babel-plugin-prismjs). This will allow you to load the minimum number of languages and plugins to satisfy your needs. See that plugin’s documentation for configuration details.

[Usage with Node](#basic-usage-node)
------------------------------------

If you want to use Prism on the server or through the command line, Prism can be used with Node.js as well. This might be useful if you’re trying to generate static HTML pages with highlighted code for environments that don’t support browser-side JS, like [AMP pages](https://www.ampproject.org/).

Example:

    const Prism = require('prismjs');
    
    // The code snippet you want to highlight, as a string
    const code = `var data = 1;`;
    
    // Returns a highlighted HTML string
    const html = Prism.highlight(code, Prism.languages.javascript, 'javascript');

Requiring `prismjs` will load the default languages: `markup`, `css`, `clike` and `javascript`. You can load more languages with the `loadLanguages()` utility, which will automatically handle any required dependencies.

Example:

    const Prism = require('prismjs');
    const loadLanguages = require('prismjs/components/');
    loadLanguages(['haml']);
    
    // The code snippet you want to highlight, as a string
    const code = `= ['hi', 'there', 'reader!'].join " "`;
    
    // Returns a highlighted HTML string
    const html = Prism.highlight(code, Prism.languages.haml, 'haml');

**Note**: Do _not_ use `loadLanguages()` with Webpack or another bundler, as this will cause Webpack to include all languages and plugins. Use the babel plugin described above.

**Note**: `loadLanguages()` will ignore unknown languages and log warning messages to the console. You can prevent the warnings by setting `loadLanguages.silent = true`.

[Supported languages](#supported-languages)
-------------------------------------------

This is the list of all 297 languages currently supported by Prism, with their corresponding alias, to use in place of `xxxx` in the `language-xxxx` (or `lang-xxxx`) class:

*   Markup —`markup`, `html`, `xml`, `svg`, `mathml`, `ssml`, `atom`, `rss`
*   CSS —`css`
*   C-like —`clike`
*   JavaScript —`javascript`, `js`
*   ABAP —`abap`
*   ABNF —`abnf`
*   ActionScript —`actionscript`
*   Ada —`ada`
*   Agda —`agda`
*   AL —`al`
*   ANTLR4 —`antlr4`, `g4`
*   Apache Configuration —`apacheconf`
*   Apex —`apex`
*   APL —`apl`
*   AppleScript —`applescript`
*   AQL —`aql`
*   Arduino —`arduino`, `ino`
*   ARFF —`arff`
*   ARM Assembly —`armasm`, `arm-asm`
*   Arturo —`arturo`, `art`
*   AsciiDoc —`asciidoc`, `adoc`
*   ASP.NET (C#) —`aspnet`
*   6502 Assembly —`asm6502`
*   Atmel AVR Assembly —`asmatmel`
*   AutoHotkey —`autohotkey`
*   AutoIt —`autoit`
*   AviSynth —`avisynth`, `avs`
*   Avro IDL —`avro-idl`, `avdl`
*   AWK —`awk`, `gawk`
*   Bash —`bash`, `sh`, `shell`
*   BASIC —`basic`
*   Batch —`batch`
*   BBcode —`bbcode`, `shortcode`
*   BBj —`bbj`
*   Bicep —`bicep`
*   Birb —`birb`
*   Bison —`bison`
*   BNF —`bnf`, `rbnf`
*   BQN —`bqn`
*   Brainfuck —`brainfuck`
*   BrightScript —`brightscript`
*   Bro —`bro`
*   BSL (1C:Enterprise) —`bsl`, `oscript`
*   C —`c`
*   C# —`csharp`, `cs`, `dotnet`
*   C++ —`cpp`
*   CFScript —`cfscript`, `cfc`
*   ChaiScript —`chaiscript`
*   CIL —`cil`
*   Cilk/C —`cilkc`, `cilk-c`
*   Cilk/C++ —`cilkcpp`, `cilk-cpp`, `cilk`
*   Clojure —`clojure`
*   CMake —`cmake`
*   COBOL —`cobol`
*   CoffeeScript —`coffeescript`, `coffee`
*   Concurnas —`concurnas`, `conc`
*   Content-Security-Policy —`csp`
*   Cooklang —`cooklang`
*   Coq —`coq`
*   Crystal —`crystal`
*   CSS Extras —`css-extras`
*   CSV —`csv`
*   CUE —`cue`
*   Cypher —`cypher`
*   D —`d`
*   Dart —`dart`
*   DataWeave —`dataweave`
*   DAX —`dax`
*   Dhall —`dhall`
*   Diff —`diff`
*   Django/Jinja2 —`django`, `jinja2`
*   DNS zone file —`dns-zone-file`, `dns-zone`
*   Docker —`docker`, `dockerfile`
*   DOT (Graphviz) —`dot`, `gv`
*   EBNF —`ebnf`
*   EditorConfig —`editorconfig`
*   Eiffel —`eiffel`
*   EJS —`ejs`, `eta`
*   Elixir —`elixir`
*   Elm —`elm`
*   Embedded Lua templating —`etlua`
*   ERB —`erb`
*   Erlang —`erlang`
*   Excel Formula —`excel-formula`, `xlsx`, `xls`
*   F# —`fsharp`
*   Factor —`factor`
*   False —`false`
*   Firestore security rules —`firestore-security-rules`
*   Flow —`flow`
*   Fortran —`fortran`
*   FreeMarker Template Language —`ftl`
*   GameMaker Language —`gml`, `gamemakerlanguage`
*   GAP (CAS) —`gap`
*   G-code —`gcode`
*   GDScript —`gdscript`
*   GEDCOM —`gedcom`
*   gettext —`gettext`, `po`
*   Gherkin —`gherkin`
*   Git —`git`
*   GLSL —`glsl`
*   GN —`gn`, `gni`
*   GNU Linker Script —`linker-script`, `ld`
*   Go —`go`
*   Go module —`go-module`, `go-mod`
*   Gradle —`gradle`
*   GraphQL —`graphql`
*   Groovy —`groovy`
*   Haml —`haml`
*   Handlebars —`handlebars`, `hbs`, `mustache`
*   Haskell —`haskell`, `hs`
*   Haxe —`haxe`
*   HCL —`hcl`
*   HLSL —`hlsl`
*   Hoon —`hoon`
*   HTTP —`http`
*   HTTP Public-Key-Pins —`hpkp`
*   HTTP Strict-Transport-Security —`hsts`
*   IchigoJam —`ichigojam`
*   Icon —`icon`
*   ICU Message Format —`icu-message-format`
*   Idris —`idris`, `idr`
*   .ignore —`ignore`, `gitignore`, `hgignore`, `npmignore`
*   Inform 7 —`inform7`
*   Ini —`ini`
*   Io —`io`
*   J —`j`
*   Java —`java`
*   JavaDoc —`javadoc`
*   JavaDoc-like —`javadoclike`
*   Java stack trace —`javastacktrace`
*   Jexl —`jexl`
*   Jolie —`jolie`
*   JQ —`jq`
*   JSDoc —`jsdoc`
*   JS Extras —`js-extras`
*   JSON —`json`, `webmanifest`
*   JSON5 —`json5`
*   JSONP —`jsonp`
*   JS stack trace —`jsstacktrace`
*   JS Templates —`js-templates`
*   Julia —`julia`
*   Keepalived Configure —`keepalived`
*   Keyman —`keyman`
*   Kotlin —`kotlin`, `kt`, `kts`
*   KuMir (КуМир) —`kumir`, `kum`
*   Kusto —`kusto`
*   LaTeX —`latex`, `tex`, `context`
*   Latte —`latte`
*   Less —`less`
*   LilyPond —`lilypond`, `ly`
*   Liquid —`liquid`
*   Lisp —`lisp`, `emacs`, `elisp`, `emacs-lisp`
*   LiveScript —`livescript`
*   LLVM IR —`llvm`
*   Log file —`log`
*   LOLCODE —`lolcode`
*   Lua —`lua`
*   Magma (CAS) —`magma`
*   Makefile —`makefile`
*   Markdown —`markdown`, `md`
*   Markup templating —`markup-templating`
*   Mata —`mata`
*   MATLAB —`matlab`
*   MAXScript —`maxscript`
*   MEL —`mel`
*   Mermaid —`mermaid`
*   METAFONT —`metafont`
*   Mizar —`mizar`
*   MongoDB —`mongodb`
*   Monkey —`monkey`
*   MoonScript —`moonscript`, `moon`
*   N1QL —`n1ql`
*   N4JS —`n4js`, `n4jsd`
*   Nand To Tetris HDL —`nand2tetris-hdl`
*   Naninovel Script —`naniscript`, `nani`
*   NASM —`nasm`
*   NEON —`neon`
*   Nevod —`nevod`
*   nginx —`nginx`
*   Nim —`nim`
*   Nix —`nix`
*   NSIS —`nsis`
*   Objective-C —`objectivec`, `objc`
*   OCaml —`ocaml`
*   Odin —`odin`
*   OpenCL —`opencl`
*   OpenQasm —`openqasm`, `qasm`
*   Oz —`oz`
*   PARI/GP —`parigp`
*   Parser —`parser`
*   Pascal —`pascal`, `objectpascal`
*   Pascaligo —`pascaligo`
*   PATROL Scripting Language —`psl`
*   PC-Axis —`pcaxis`, `px`
*   PeopleCode —`peoplecode`, `pcode`
*   Perl —`perl`
*   PHP —`php`
*   PHPDoc —`phpdoc`
*   PHP Extras —`php-extras`
*   PlantUML —`plant-uml`, `plantuml`
*   PL/SQL —`plsql`
*   PowerQuery —`powerquery`, `pq`, `mscript`
*   PowerShell —`powershell`
*   Processing —`processing`
*   Prolog —`prolog`
*   PromQL —`promql`
*   .properties —`properties`
*   Protocol Buffers —`protobuf`
*   Pug —`pug`
*   Puppet —`puppet`
*   Pure —`pure`
*   PureBasic —`purebasic`, `pbfasm`
*   PureScript —`purescript`, `purs`
*   Python —`python`, `py`
*   Q# —`qsharp`, `qs`
*   Q (kdb+ database) —`q`
*   QML —`qml`
*   Qore —`qore`
*   R —`r`
*   Racket —`racket`, `rkt`
*   Razor C# —`cshtml`, `razor`
*   React JSX —`jsx`
*   React TSX —`tsx`
*   Reason —`reason`
*   Regex —`regex`
*   Rego —`rego`
*   Ren'py —`renpy`, `rpy`
*   ReScript —`rescript`, `res`
*   reST (reStructuredText) —`rest`
*   Rip —`rip`
*   Roboconf —`roboconf`
*   Robot Framework —`robotframework`, `robot`
*   Ruby —`ruby`, `rb`
*   Rust —`rust`
*   SAS —`sas`
*   Sass (Sass) —`sass`
*   Sass (SCSS) —`scss`
*   Scala —`scala`
*   Scheme —`scheme`
*   Shell session —`shell-session`, `sh-session`, `shellsession`
*   Smali —`smali`
*   Smalltalk —`smalltalk`
*   Smarty —`smarty`
*   SML —`sml`, `smlnj`
*   Solidity (Ethereum) —`solidity`, `sol`
*   Solution file —`solution-file`, `sln`
*   Soy (Closure Template) —`soy`
*   SPARQL —`sparql`, `rq`
*   Splunk SPL —`splunk-spl`
*   SQF: Status Quo Function (Arma 3) —`sqf`
*   SQL —`sql`
*   Squirrel —`squirrel`
*   Stan —`stan`
*   Stata Ado —`stata`
*   Structured Text (IEC 61131-3) —`iecst`
*   Stylus —`stylus`
*   SuperCollider —`supercollider`, `sclang`
*   Swift —`swift`
*   Systemd configuration file —`systemd`
*   T4 templating —`t4-templating`
*   T4 Text Templates (C#) —`t4-cs`, `t4`
*   T4 Text Templates (VB) —`t4-vb`
*   TAP —`tap`
*   Tcl —`tcl`
*   Template Toolkit 2 —`tt2`
*   Textile —`textile`
*   TOML —`toml`
*   Tremor —`tremor`, `trickle`, `troy`
*   Turtle —`turtle`, `trig`
*   Twig —`twig`
*   TypeScript —`typescript`, `ts`
*   TypoScript —`typoscript`, `tsconfig`
*   UnrealScript —`unrealscript`, `uscript`, `uc`
*   UO Razor Script —`uorazor`
*   URI —`uri`, `url`
*   V —`v`
*   Vala —`vala`
*   VB.Net —`vbnet`
*   Velocity —`velocity`
*   Verilog —`verilog`
*   VHDL —`vhdl`
*   vim —`vim`
*   Visual Basic —`visual-basic`, `vb`, `vba`
*   WarpScript —`warpscript`
*   WebAssembly —`wasm`
*   Web IDL —`web-idl`, `webidl`
*   WGSL —`wgsl`
*   Wiki markup —`wiki`
*   Wolfram language —`wolfram`, `mathematica`, `nb`, `wl`
*   Wren —`wren`
*   Xeora —`xeora`, `xeoracube`
*   XML doc (.net) —`xml-doc`
*   Xojo (REALbasic) —`xojo`
*   XQuery —`xquery`
*   YAML —`yaml`, `yml`
*   YANG —`yang`
*   Zig —`zig`

Couldn’t find the language you were looking for? [Request it](https://github.com/PrismJS/prism/issues)!

[Plugins](#plugins)
-------------------

Plugins are additional scripts (and CSS code) that extend Prism’s functionality. Many of the following plugins are official, but are released as plugins to keep the Prism Core small for those who don’t need the extra functionality.

*   [Autolinker](https://prismjs.com/plugins/autolinker)
    
    Converts URLs and emails in code to clickable links. Parses Markdown links in comments.
    
*   [Autoloader](https://prismjs.com/plugins/autoloader)
    
    Automatically loads the needed languages to highlight the code blocks.
    
*   [Command Line](https://prismjs.com/plugins/command-line)
    
    Display a command line with a prompt and, optionally, the output/response from the commands.
    
*   [Copy to Clipboard](https://prismjs.com/plugins/copy-to-clipboard)
    
    Add a button that copies the code block to the clipboard when clicked.
    
*   [Custom Class](https://prismjs.com/plugins/custom-class)
    
    This plugin allows you to prefix Prism’s default classes (`.comment` can become `.namespace--comment`) or replace them with your defined ones (like `.editor__comment`). You can even add new classes.
    
*   [Data URI Highlight](https://prismjs.com/plugins/data-uri-highlight)
    
    Highlights data-URI contents.
    
*   [Diff Highlight](https://prismjs.com/plugins/diff-highlight)
    
    Highlight the code inside diff blocks.
    
*   [Download Button](https://prismjs.com/plugins/download-button)
    
    A button in the toolbar of a code block adding a convenient way to download a code file.
    
*   [File Highlight](https://prismjs.com/plugins/file-highlight)
    
    Fetch external files and highlight them with Prism. Used on the Prism website itself.
    
*   [Filter highlightAll](https://prismjs.com/plugins/filter-highlight-all)
    
    Filters the elements the `highlightAll` and `highlightAllUnder` methods actually highlight.
    
*   [Highlight Keywords](https://prismjs.com/plugins/highlight-keywords)
    
    Adds special CSS classes for each keyword for fine-grained highlighting.
    
*   [Inline Color](https://prismjs.com/plugins/inline-color)
    
    Adds a small inline preview for colors in style sheets.
    
*   [JSONP Highlight](https://prismjs.com/plugins/jsonp-highlight)
    
    Fetch content with JSONP and highlight some interesting content (e.g. GitHub/Gists or Bitbucket API).
    
*   [Keep Markup](https://prismjs.com/plugins/keep-markup)
    
    Prevents custom markup from being dropped out during highlighting.
    
*   [Line Highlight](https://prismjs.com/plugins/line-highlight)
    
    Highlights specific lines and/or line ranges.
    
*   [Line Numbers](https://prismjs.com/plugins/line-numbers)
    
    Line number at the beginning of code lines.
    
*   [Match braces](https://prismjs.com/plugins/match-braces)
    
    Highlights matching braces.
    
*   [Normalize Whitespace](https://prismjs.com/plugins/normalize-whitespace)
    
    Supports multiple operations to normalize whitespace in code blocks.
    
*   [Previewers](https://prismjs.com/plugins/previewers)
    
    Previewers for angles, colors, gradients, easing and time.
    
*   [Remove Initial Line Feed](https://prismjs.com/plugins/remove-initial-line-feed)
    
    Removes the initial line feed in code blocks.
    
*   [Show Invisibles](https://prismjs.com/plugins/show-invisibles)
    
    Show hidden characters such as tabs and line breaks.
    
*   [Show Language](https://prismjs.com/plugins/show-language)
    
    Display the highlighted language in code blocks (inline code does not show the label).
    
*   [Toolbar](https://prismjs.com/plugins/toolbar)
    
    Attach a toolbar for plugins to easily register buttons on the top of a code block.
    
*   [Treeview](https://prismjs.com/plugins/treeview)
    
    A language with special styles to highlight file system tree structures.
    
*   [Unescaped Markup](https://prismjs.com/plugins/unescaped-markup)
    
    Write markup without having to escape anything.
    
*   [WebPlatform Docs](https://prismjs.com/plugins/wpd)

No assembly required to use them. Just select them in the [download](https://prismjs.com/download) page.

It’s very easy to [write your own Prism plugins](https://prismjs.com/extending#writing-plugins). Did you write a plugin for Prism that you want added to this list? [Send a pull request](https://github.com/PrismJS/plugins/)!

[Third-party language definitions](#third-party-language-definitions)
---------------------------------------------------------------------

*   [SassDoc Sass/Scss comments](https://github.com/SassDoc/prism-scss-sassdoc)
*   [Liquibase CLI Bash language extension](https://github.com/Liquibase/prism-liquibase)

[Third-party tutorials](#third-party-tutorials)
-----------------------------------------------

Several tutorials have been written by members of the community to help you integrate Prism into multiple different website types and configurations:

*   [How to Add Prism.js Syntax Highlighting to Your WordPress Site](https://startblogging101.com/how-to-add-prism-js-syntax-highlighting-wordpress/)
*   [Escape HTML Inside `<code>` or `<pre>` Tag to Entities to Display Raw Code with PrismJS](https://websitebeaver.com/escape-html-inside-code-or-pre-tag-to-entities-to-display-raw-code-with-prismjs)
*   [Adding a Syntax Highlighter Shortcode Using Prism.js | WPTuts+](http://wp.tutsplus.com/tutorials/plugins/adding-a-syntax-highlighter-shortcode-using-prism-js/)
*   [Implement PrismJs Syntax Highlighting to your Blogger/BlogSpot](https://www.stramaxon.com/2012/07/prism-syntax-highlighter-for-blogger.html)
*   [How To Re-Run Prism.js On AJAX Content](https://schier.co/blog/2013/01/07/how-to-re-run-prismjs-on-ajax-content.html)
*   [Highlight your code syntax with Prism.js](https://www.semisedlak.com/highlight-your-code-syntax-with-prismjs)
*   [A code snippet content element powered by Prism.js for TYPO3 CMS](https://usetypo3.com/fs-code-snippet.html)

*   [Code syntax highlighting in Gutenberg, WordPress block editor](https://mkaz.blog/wordpress/code-syntax-highlighting-in-gutenberg/)
*   [Code Highlighting with Prism.js in Drupal](https://karlkaufmann.com/writing/technotes/code-highlighting-prism-drupal)
*   [Code highlighting in React using Prism.js](https://betterstack.dev/blog/code-highlighting-in-react-using-prismjs/)

*   [PrismJS Tutorial | Implement Prism in HTML and React](https://itsmycode.com/prismjs-tutorial/)
*   Code syntax highlighting in Pug with [:highlight](https://webdiscus.github.io/pug-loader/pug-filters/highlight.html) and [:markdown](https://webdiscus.github.io/pug-loader/pug-filters/markdown.html) filters using [pug-loader](https://github.com/webdiscus/pug-loader) and Prism.js

Please note that the tutorials listed here are not verified to contain correct information. Read at your risk and always check the official documentation here if something doesn’t work. 🙂

Have you written a tutorial about Prism that’s not already included here? Send a pull request!

[Credits](#credits)
-------------------

*   Special thanks to [Michael Schmidt](https://github.com/RunDevelopment), [James DiGioia](https://github.com/mAAdhaTTah), [Golmote](https://github.com/Golmote) and [Jannik Zschiesche](https://github.com/apfelbox) for their contributions and for being **amazing maintainers**. Prism would not have been able to keep up without their help.
*   To [Roman Komarov](https://twitter.com/kizmarh) for his contributions, feedback and testing.
*   To [Zachary Forrest](https://twitter.com/zdfs) for [coming up with the name “Prism”](https://twitter.com/zdfs/statuses/217834980871639041).
*   To [stellarr](https://stellarr.deviantart.com/) for the [spectrum background](https://stellarr.deviantart.com/art/Spectra-Wallpaper-Pack-97785901) used on this page.
*   To [Jason Hobbs](https://twitter.com/thecodezombie) for [encouraging me](https://twitter.com/thecodezombie/status/217663703825399809) to release this script as standalone.
