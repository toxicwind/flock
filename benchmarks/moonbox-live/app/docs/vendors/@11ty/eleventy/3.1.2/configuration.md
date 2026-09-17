Breadcrumbs:

*   [Eleventy Documentation](https://www.11ty.dev/docs/)
*   [Guide](https://www.11ty.dev/docs/projects/)

On this page

*   [Default filenames](#default-filenames)
*   [Configuration Options](#configuration-options)
    *   [Input Directory](#input-directory)
    *   [Directory for Includes](#directory-for-includes)
    *   [Directory for Layouts (Optional)](#directory-for-layouts-optional)
    *   [Directory for Global Data Files](#directory-for-global-data-files)
    *   [Output Directory](#output-directory)
    *   [Default template engine for Markdown files](#default-template-engine-for-markdown-files)
    *   [Default template engine for HTML files](#default-template-engine-for-html-files)
    *   [Template Formats](#template-formats)
    *   [Enable Quiet Mode to Reduce Console Noise](#enable-quiet-mode-to-reduce-console-noise)
    *   [Deploy to a subdirectory with a Path Prefix](#deploy-to-a-subdirectory-with-a-path-prefix)
    *   [Change Base File Name for Data Files](#change-base-file-name-for-data-files)
    *   [Change File Suffix for Data Files](#change-file-suffix-for-data-files)
    *   [Transforms](#transforms)
    *   [Linters](#linters)
    *   [Data Filter Selectors](#data-filter-selectors)
    *   [TypeScript Type Definitions](#type-script-type-definitions)
    *   [Removed Features](#removed-features)
    *   [Documentation Moved to Dedicated Pages](#documentation-moved-to-dedicated-pages)

Configuration files are optional. Add an `eleventy.config.js` file to the root directory of your project (read more about [default configuration filenames](#default-filenames)) to configure Eleventy to your own project’s needs. It might look like this:

eleventy.config.js

    export default async function(eleventyConfig) {	// Configure Eleventy};

    module.exports = async function(eleventyConfig) {	// Configure Eleventy};

There are a few different ways to [shape your configuration file](https://www.11ty.dev/docs/config-shapes/). Added in v3.0.0Eleventy v3 added support for both ESM and Asynchronous callbacks.

*   Add [Filters](https://www.11ty.dev/docs/filters/).
*   Add [Shortcodes](https://www.11ty.dev/docs/shortcodes/).
*   Add [Custom Tags](https://www.11ty.dev/docs/custom-tags/).
*   Add [JavaScript Template Functions](https://www.11ty.dev/docs/languages/javascript/#javascript-template-functions)
*   Add custom [Collections](https://www.11ty.dev/docs/collections/) and use [Advanced Collection Filtering and Sorting](https://www.11ty.dev/docs/collections/#advanced-custom-filtering-and-sorting).
*   Add [Plugins](https://www.11ty.dev/docs/plugins/).

Default filenames
-----------------

We look for the following configuration files:

1.  `.eleventy.js`
2.  `eleventy.config.js` Added in v2.0.0
3.  `eleventy.config.mjs` Added in v3.0.0
4.  `eleventy.config.cjs` Added in v2.0.0

The first configuration file found is used. The others are ignored.

Configuration Options
---------------------

### Input Directory

Controls the top level directory/file/glob that we’ll use to look for templates.

Input Directory

_Object Key_

`dir.input`

_Default Value_

`.` _(current directory)_

_Valid Options_

Any valid directory.

_Configuration API_

`eleventyConfig.setInputDirectory()` Added in v3.0.0

_Command Line Override_

`--input`

#### Command Line

    # The current directorynpx @11ty/eleventy --input=.# A single filenpx @11ty/eleventy --input=README.md# A glob of filesnpx @11ty/eleventy --input=*.md# A subdirectorynpx @11ty/eleventy --input=views

#### Configuration

Via named export (order doesn’t matter). Note that there are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

eleventy.config.js

    export const config = {  dir: {    input: "views"  }};

    module.exports.config = {  dir: {    input: "views"  }};

Or via method (not available in plugins) Added in v3.0.0:

eleventy.config.js

    export default function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.  eleventyConfig.setInputDirectory("views");};

    module.exports = function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.  eleventyConfig.setInputDirectory("views");};

### Directory for Includes

The includes directory is meant for [Eleventy layouts](https://www.11ty.dev/docs/layouts/), include files, extends files, partials, or macros. These files will not be processed as full template files, but can be consumed by other templates.

Includes Directory

_Object Key_

`dir.includes`

_Default_

`_includes`

_Valid Options_

Any valid directory inside of `dir.input` (an empty string `""` is supported)

_Configuration API_

`eleventyConfig.setIncludesDirectory()` Added in v3.0.0

_Command Line Override_

_None_

Via named export (order doesn’t matter). Note that there are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

eleventy.config.js

    export const config = {  dir: {		// ⚠️ This value is relative to your input directory.    includes: "my_includes"  }};

    module.exports.config = {  dir: {		// ⚠️ This value is relative to your input directory.    includes: "my_includes"  }};

Or via method (not available in plugins) Added in v3.0.0:

eleventy.config.js

    export default function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.	// This is relative to your input directory!  eleventyConfig.setIncludesDirectory("my_includes");};

    module.exports = function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.	// This is relative to your input directory!  eleventyConfig.setIncludesDirectory("my_includes");};

### Directory for Layouts (Optional)

This configuration option is optional but useful if you want your [Eleventy layouts](https://www.11ty.dev/docs/layouts/) to live outside of the [Includes directory](#directory-for-includes). Just like the [Includes directory](#directory-for-includes), these files will not be processed as full template files, but can be consumed by other templates.

WARNING:

Includes Directory

_Object Key_

`dir.layouts`

_Default_

_The value in `dir.includes`_

_Valid Options_

Any valid directory inside of `dir.input` (an empty string `""` is supported)

_Configuration API_

`eleventyConfig.setLayoutsDirectory()` Added in v3.0.0

_Command Line Override_

_None_

Via named export (order doesn’t matter). Note that there are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

eleventy.config.js

    export const config = {  dir: {    // These are both relative to your input directory!    includes: "_includes",    layouts: "_layouts",  }};

    module.exports.config = {  dir: {    // These are both relative to your input directory!    includes: "_includes",    layouts: "_layouts",  }};

Or via method (not available in plugins) Added in v3.0.0:

eleventy.config.js

    export default function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.	// This is relative to your input directory!  eleventyConfig.setLayoutsDirectory("_layouts");};

    module.exports = function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.	// This is relative to your input directory!  eleventyConfig.setLayoutsDirectory("_layouts");};

### Directory for Global Data Files

Controls the directory inside which the global data template files, available to all templates, can be found. Read more about [Global Data Files](https://www.11ty.dev/docs/data-global/).

Data Files Directory

_Object Key_

`dir.data`

_Default_

`_data`

_Valid Options_

Any valid directory inside of `dir.input`

_Configuration API_

`eleventyConfig.setDataDirectory()` Added in v3.0.0

_Command Line Override_

_None_

Via named export (order doesn’t matter). Note that there are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

eleventy.config.js

    export const config = {  dir: {    // ⚠️ This value is relative to your input directory.    data: "lore",  }};

    module.exports.config = {  dir: {    // ⚠️ This value is relative to your input directory.    data: "lore",  }};

Or via method (not available in plugins) Added in v3.0.0:

eleventy.config.js

    export default function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.  eleventyConfig.setDataDirectory("lore");};

    module.exports = function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.  eleventyConfig.setDataDirectory("lore");};

### Output Directory

Controls the directory inside which the finished templates will be written to.

Output Directory

_Object Key_

`dir.output`

_Default_

`_site`

_Valid Options_

Any string that will work as a directory name. Eleventy creates this if it doesn’t exist.

_Configuration API_

`eleventyConfig.setOutputDirectory()` Added in v3.0.0

_Command Line Override_

`--output`

#### Command Line

    npx @11ty/eleventy --output=_site

#### Configuration

Via named export (order doesn’t matter). Note that there are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

eleventy.config.js

    export const config = {  dir: {		output: "dist",  }};

    module.exports.config = {  dir: {		output: "dist",  }};

Or via method (not available in plugins) Added in v3.0.0:

eleventy.config.js

    export default function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.  eleventyConfig.setOutputDirectory("dist");};

    module.exports = function(eleventyConfig) {	// Order matters, put this at the top of your configuration file.  eleventyConfig.setOutputDirectory("dist");};

### Default template engine for Markdown files

Markdown files run through this template engine before transforming to HTML.

Markdown Template Engine

_Object Key_

`markdownTemplateEngine`

_Default_

`liquid`

_Valid Options_

A valid [template engine short name](https://www.11ty.dev/docs/languages/) or `false`

_Command Line Override_

_None_

eleventy.config.js

    export const config = {  markdownTemplateEngine: "njk",};

    module.exports.config = {  markdownTemplateEngine: "njk",};

There are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

### Default template engine for HTML files

HTML templates run through this template engine before transforming to (better) HTML.

HTML Template Engine

_Object Key_

`htmlTemplateEngine`

_Default_

`liquid`

_Valid Options_

A valid [template engine short name](https://www.11ty.dev/docs/languages/) or `false`

_Command Line Override_

_None_

eleventy.config.js

    export const config = {  htmlTemplateEngine: "njk",};

    module.exports.config = {  htmlTemplateEngine: "njk",};

There are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

### Template Formats

Specify which types of templates should be transformed.

Template Formats

_Object Key_

`templateFormats`

_Default_

`html,liquid,ejs,md,hbs,mustache,haml,pug,njk,11ty.js`

_Valid Options_

Array of [template engine short names](https://www.11ty.dev/docs/languages/)

_Command Line Override_

`--formats` _(accepts a comma separated string)_

_Configuration API_

`setTemplateFormats` and `addTemplateFormats`

INFO:

**Case sensitivity**: File extensions should be considered case insensitive, cross-platform. While macOS already behaves this way (by default), other operating systems require additional Eleventy code to enable this behavior.

#### Command Line

    npx @11ty/eleventy --formats=html,liquid,njk
    

#### Configuration File Static Export

eleventy.config.js

    export const config = {  templateFormats: ["html", "liquid", "njk"],};

    module.exports.config = {  templateFormats: ["html", "liquid", "njk"],};

There are many [different shapes of configuration file](https://www.11ty.dev/docs/config-shapes/).

#### Configuration API

eleventy.config.js

    export default function (eleventyConfig) {	// Reset to this value	eleventyConfig.setTemplateFormats("html,liquid,njk");	// Additive to existing	eleventyConfig.addTemplateFormats("pug,haml");	// Or:	// eleventyConfig.setTemplateFormats([ "html", "liquid", "njk" ]);	// eleventyConfig.addTemplateFormats([ "pug", "haml" ]);};

    module.exports = function (eleventyConfig) {	// Reset to this value	eleventyConfig.setTemplateFormats("html,liquid,njk");	// Additive to existing	eleventyConfig.addTemplateFormats("pug,haml");	// Or:	// eleventyConfig.setTemplateFormats([ "html", "liquid", "njk" ]);	// eleventyConfig.addTemplateFormats([ "pug", "haml" ]);};

### Enable Quiet Mode to Reduce Console Noise

In order to maximize user-friendliness to beginners, Eleventy will show each file it processes and the output file. To disable this noisy console output, use quiet mode!

Quiet Mode

_Default_

`false`

_Valid Options_

`true` or `false`

_Command Line Override_

`--quiet`

eleventy.config.js

    export default function (eleventyConfig) {	eleventyConfig.setQuietMode(true);};

    module.exports = function (eleventyConfig) {	eleventyConfig.setQuietMode(true);};

The command line will override any setting in configuration:

    npx @11ty/eleventy --quiet

### Deploy to a subdirectory with a Path Prefix

If your site lives in a different subdirectory (particularly useful with GitHub pages), use pathPrefix to specify this. When paired with the [HTML `<base>` plugin](https://www.11ty.dev/docs/plugins/html-base/) it will transform any absolute URLs in your HTML to include this folder name and does **not** affect where things go in the output folder.

Path Prefix

_Object Key_

`pathPrefix`

_Default_

`/`

_Valid Options_

A prefix directory added to urls in HTML files

_Command Line Override_

`--pathprefix`

eleventy.config.js

    import { HtmlBasePlugin } from "@11ty/eleventy";export default function (eleventyConfig) {	eleventyConfig.addPlugin(HtmlBasePlugin);};export const config = {	pathPrefix: "/eleventy-base-blog/",}

    module.exports = async function (eleventyConfig) {	const { HtmlBasePlugin } = await import("@11ty/eleventy");	eleventyConfig.addPlugin(HtmlBasePlugin);};module.exports.config = {	pathPrefix: "/eleventy-base-blog/",}

Deploy to https://11ty.github.io/eleventy-base-blog/ on GitHub pages without modifying your config. This allows you to use the same code-base to deploy to either GitHub pages or Netlify, like the [`eleventy-base-blog`](https://github.com/11ty/eleventy-base-blog) project does.

    npx @11ty/eleventy --pathprefix=eleventy-base-blog

### Change Base File Name for Data Files

Added in v2.0.0 When using [Directory Specific Data Files](https://www.11ty.dev/docs/data-template-dir/), looks for data files that match the current folder name. You can override this behavior to a static string with the `setDataFileBaseName` method.

File Suffix

_Configuration API_

`setDataFileBaseName`

_Default_

_Current folder name_

_Valid Options_

String

_Command Line Override_

_None_

eleventy.config.js

    export default function (eleventyConfig) {	// Looks for index.json and index.11tydata.json instead of using folder names	eleventyConfig.setDataFileBaseName("index");};

    module.exports = function (eleventyConfig) {	// Looks for index.json and index.11tydata.json instead of using folder names	eleventyConfig.setDataFileBaseName("index");};

### Change File Suffix for Data Files

Added in v2.0.0 When using [Template and Directory Specific Data Files](https://www.11ty.dev/docs/data-template-dir/), to prevent file name conflicts with non-Eleventy files in the project directory, we scope these files with a unique-to-Eleventy suffix. This suffix is customizable using the `setDataFileSuffixes` configuration API method.

File Suffix

_Configuration API_

`setDataFileSuffixes`

_Default_

`[".11tydata", ""]`

_Valid Options_

Array

_Command Line Override_

_None_

For example, using `".11tydata"` will search for `*.11tydata.js` and `*.11tydata.json` data files. The empty string (`""`) here represents a file without a suffix—and this entry only applies to `*.json` data files.

This feature can also be used to disable Template and Directory Data Files altogether with an empty array (`[]`).

Read more about [Template and Directory Specific Data Files](https://www.11ty.dev/docs/data-template-dir/).

eleventy.config.js

    export default function (eleventyConfig) {	// e.g. file.json and file.11tydata.json	eleventyConfig.setDataFileSuffixes([".11tydata", ""]);	// e.g. file.11tydata.json	eleventyConfig.setDataFileSuffixes([".11tydata"]);	// No data files are used.	eleventyConfig.setDataFileSuffixes([]);};

    module.exports = function (eleventyConfig) {	// e.g. file.json and file.11tydata.json	eleventyConfig.setDataFileSuffixes([".11tydata", ""]);	// e.g. file.11tydata.json	eleventyConfig.setDataFileSuffixes([".11tydata"]);	// No data files are used.	eleventyConfig.setDataFileSuffixes([]);};

_**Backwards Compatibility Note**_ (`v2.0.0`)

Prior to v2.0.0 this feature was exposed using a `jsDataFileSuffix` property in the configuration return object. When the `setDataFileSuffixes` method has not been used, Eleventy maintains backwards compatibility for old projects by using this property as a fallback.

eleventy.config.js

    export default function (eleventyConfig) {	return {		jsDataFileSuffix: ".11tydata",	};};

    module.exports = function (eleventyConfig) {	return {		jsDataFileSuffix: ".11tydata",	};};

### Transforms

*   Documented moved to [Transforms](https://www.11ty.dev/docs/transforms/).

### Linters

Similar to Transforms, Linters are provided to analyze a template’s output without modifying it.

Linters

_Configuration API_

`addLinter`

_Object Key_

_N/A_

_Valid Options_

Callback function

_Command Line Override_

_None_

eleventy.config.js

    export default function (eleventyConfig) {	// Sync or async	eleventyConfig.addLinter("linter-name", async function (content) {		console.log(this.inputPath);		console.log(this.outputPath);		// Eleventy 2.0+ has full access to Eleventy’s `page` variable		console.log(this.page.inputPath);		console.log(this.page.outputPath);	});};

    module.exports = function (eleventyConfig) {	// Sync or async	eleventyConfig.addLinter("linter-name", async function (content) {		console.log(this.inputPath);		console.log(this.outputPath);		// Eleventy 2.0+ has full access to Eleventy’s `page` variable		console.log(this.page.inputPath);		console.log(this.page.outputPath);	});};

**Linters Example: Use Inclusive Language**

Inspired by the [CSS Tricks post _Words to Avoid in Educational Writing_](https://css-tricks.com/words-avoid-educational-writing/), this linter will log a warning to the console when it finds a trigger word in a markdown file.

This example has been packaged as a plugin in [`eleventy-plugin-inclusive-language`](https://www.11ty.dev/docs/plugins/inclusive-language/).

**Filename** eleventy.config.js

    export default function (eleventyConfig) {	eleventyConfig.addLinter(		"inclusive-language",		function (content, inputPath, outputPath) {			let words =				"simply,obviously,basically,of course,clearly,just,everyone knows,however,easy".split(					","				);			// Eleventy 1.0+: use this.inputPath and this.outputPath instead			if (inputPath.endsWith(".md")) {				for (let word of words) {					let regexp = new RegExp("\\b(" + word + ")\\b", "gi");					if (content.match(regexp)) {						console.warn(							`Inclusive Language Linter (${inputPath}) Found: ${word}`						);					}				}			}		}	);};

### Data Filter Selectors

A `Set` of [`lodash` selectors](https://lodash.com/docs/4.17.15#get) that allow you to include data from the data cascade in the output from `--to=json`, `--to=ndjson`.

eleventy.config.js

    export default function (eleventyConfig) {	eleventyConfig.dataFilterSelectors.add("page");	eleventyConfig.dataFilterSelectors.delete("page");};

    module.exports = function (eleventyConfig) {	eleventyConfig.dataFilterSelectors.add("page");	eleventyConfig.dataFilterSelectors.delete("page");};

This will now include a `data` property in your JSON output that includes the `page` variable for each matching template.

### TypeScript Type Definitions

This may enable some extra autocomplete features in your IDE (where supported).

eleventy.config.js

    /** @param {import("@11ty/eleventy").UserConfig} eleventyConfig */export default function (eleventyConfig) {	// …};

    /** @param {import("@11ty/eleventy").UserConfig} eleventyConfig */module.exports = function (eleventyConfig) {	// …};

*   Related: [GitHub #2091](https://github.com/11ty/eleventy/pull/2091) and [GitHub #3097](https://github.com/11ty/eleventy/issues/3097)

### Removed Features

#### Change exception case suffix for HTML files

Feature Removal

The `htmlOutputSuffix` feature was removed in Eleventy 3.0. You can read about the feature on the [v2 documentation](https://v2-0-1.11ty.dev/docs/config/#change-exception-case-suffix-for-html-files). Related: [GitHub #3327](https://github.com/11ty/eleventy/issues/3327).

### Documentation Moved to Dedicated Pages

#### Copy Files to Output using Passthrough File Copy

Files found (that don’t have a valid template engine) from opt-in file extensions in `templateFormats` will passthrough to the output directory. Read more about [Passthrough Copy](https://www.11ty.dev/docs/copy/).

#### Data Deep Merge

*   Documentation for [Data Deep Merging has been moved to its own page](https://www.11ty.dev/docs/data-deep-merge/) under the Data Cascade.

#### Customize Front Matter Parsing Options

*   Documented at [Customize Front Matter Parsing](https://www.11ty.dev/docs/data-frontmatter-customize/).

#### Watch JavaScript Dependencies

*   Documented at [Watch and Serve Configuration](https://www.11ty.dev/docs/watch-serve/).

#### Add Your Own Watch Targets

*   Documented at [Watch and Serve Configuration](https://www.11ty.dev/docs/watch-serve/).

#### Override Browsersync Server Options

*   Documented at [Watch and Serve Configuration](https://www.11ty.dev/docs/watch-serve/).

#### Transforms

*   Documented at [Transforms](https://www.11ty.dev/docs/transforms/).

* * *

### Other pages in Eleventy Projects

*   [Get Started](https://www.11ty.dev/docs/)
*   [Command Line Usage](https://www.11ty.dev/docs/usage/)
*   [Add a Configuration File](https://www.11ty.dev/docs/config/)
*   [Copy Files to Output](https://www.11ty.dev/docs/copy/)
*   [Add CSS, JS, Fonts](https://www.11ty.dev/docs/assets/)
*   [Importing Content](https://www.11ty.dev/docs/migrate/)
*   [Configure Templates with Data](https://www.11ty.dev/docs/data-configuration/)
    *   [Permalinks](https://www.11ty.dev/docs/permalinks/)
    *   [Layouts](https://www.11ty.dev/docs/layouts/)
    *   [Collections](https://www.11ty.dev/docs/collections/)
        *   [Collections API](https://www.11ty.dev/docs/collections-api/)
    *   [Content Dates](https://www.11ty.dev/docs/dates/)
    *   [Create Pages From Data](https://www.11ty.dev/docs/pages-from-data/)
        *   [Pagination](https://www.11ty.dev/docs/pagination/)
        *   [Pagination Navigation](https://www.11ty.dev/docs/pagination/nav/)
*   [Using Data in Templates](https://www.11ty.dev/docs/data/)
    *   [Eleventy Supplied Data](https://www.11ty.dev/docs/data-eleventy-supplied/)
    *   [Data Cascade](https://www.11ty.dev/docs/data-cascade/)
        *   [Front Matter Data](https://www.11ty.dev/docs/data-frontmatter/)
            *   [Custom Front Matter](https://www.11ty.dev/docs/data-frontmatter-customize/)
        *   [Template & Directory Data Files](https://www.11ty.dev/docs/data-template-dir/)
        *   [Global Data Files](https://www.11ty.dev/docs/data-global/)
        *   [Config Global Data](https://www.11ty.dev/docs/data-global-custom/)
        *   [Computed Data](https://www.11ty.dev/docs/data-computed/)
    *   [JavaScript Data Files](https://www.11ty.dev/docs/data-js/)
    *   [Custom Data File Formats](https://www.11ty.dev/docs/data-custom/)
    *   [Validate Data](https://www.11ty.dev/docs/data-validate/)
*   [Template Languages](https://www.11ty.dev/docs/languages/)
    *   [HTML](https://www.11ty.dev/docs/languages/html/)
    *   [Markdown](https://www.11ty.dev/docs/languages/markdown/)
        *   [MDX](https://www.11ty.dev/docs/languages/mdx/)
    *   [JavaScript](https://www.11ty.dev/docs/languages/javascript/)
        *   [JSX](https://www.11ty.dev/docs/languages/jsx/)
        *   [TypeScript](https://www.11ty.dev/docs/languages/typescript/)
    *   [Custom](https://www.11ty.dev/docs/languages/custom/)
    *   [WebC](https://www.11ty.dev/docs/languages/webc/)
    *   [Nunjucks](https://www.11ty.dev/docs/languages/nunjucks/)
    *   [Liquid](https://www.11ty.dev/docs/languages/liquid/)
    *   [Handlebars](https://www.11ty.dev/docs/languages/handlebars/)
    *   [Mustache](https://www.11ty.dev/docs/languages/mustache/)
    *   [EJS](https://www.11ty.dev/docs/languages/ejs/)
    *   [HAML](https://www.11ty.dev/docs/languages/haml/)
    *   [Pug](https://www.11ty.dev/docs/languages/pug/)
    *   [Sass](https://www.11ty.dev/docs/languages/sass/)
    *   [Virtual Templates](https://www.11ty.dev/docs/virtual-templates/)
    *   [Overriding Languages](https://www.11ty.dev/docs/template-overrides/)
*   Template Features
    *   [Ignore Files](https://www.11ty.dev/docs/ignores/)
    *   [Preprocess Content](https://www.11ty.dev/docs/config-preprocessors/)
    *   [Postprocess Content](https://www.11ty.dev/docs/transforms/)
    *   [Filters](https://www.11ty.dev/docs/filters/)
        *   [`url`](https://www.11ty.dev/docs/filters/url/)
        *   [`slugify`](https://www.11ty.dev/docs/filters/slugify/)
        *   [`log`](https://www.11ty.dev/docs/filters/log/)
        *   [`get*CollectionItem`](https://www.11ty.dev/docs/filters/collection-items/)
        *   [`inputPathToUrl`](https://www.11ty.dev/docs/filters/inputpath-to-url/)
    *   [Shortcodes](https://www.11ty.dev/docs/shortcodes/)
        *   [`getBundle`](https://www.11ty.dev/docs/plugins/bundle/)
        *   [`getBundleFileUrl`](https://www.11ty.dev/docs/plugins/bundle/)
*   [Environment Variables](https://www.11ty.dev/docs/environment-vars/)
*   [Internationalization (i18n)](https://www.11ty.dev/docs/i18n/)
*   [Development Servers](https://www.11ty.dev/docs/watch-serve/)
    *   [Eleventy Dev Server](https://www.11ty.dev/docs/dev-server/)
    *   [Vite](https://www.11ty.dev/docs/server-vite/)
*   [Common Pitfalls](https://www.11ty.dev/docs/pitfalls/)
*   [Advanced](https://www.11ty.dev/docs/advanced/)
    *   [Release History](https://www.11ty.dev/docs/versions/)
    *   [Programmatic API](https://www.11ty.dev/docs/programmatic/)
    *   [Configuration Events](https://www.11ty.dev/docs/events/)
    *   [Order of Operations](https://www.11ty.dev/docs/advanced-order/)
