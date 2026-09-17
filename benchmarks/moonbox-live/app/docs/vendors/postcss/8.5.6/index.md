*   [Setup](https://github.com/postcss/postcss#usage)
*   [Docs](https://postcss.org/docs/)
*   [Plugins](https://postcss.org/docs/postcss-plugins)
*   [API](https://postcss.org/api/)
*   [Logo](https://github.com/postcss/brand)

![PostCSS logo](https://postcss.org/assets/postcss-CsElRNOW.svg)

PostCSS
-------

A tool for transforming CSS with JavaScript

Add vendor prefixes to CSS rules using values from Can I Use. [Autoprefixer](https://github.com/postcss/autoprefixer) will use the data based on current browser popularity and property support to apply prefixes for you.

:fullscreen {
}

CSS input

:-webkit-full-screen {
}
:-ms-fullscreen {
}
:fullscreen {
}

CSS output

[PostCSS Preset Env](https://preset-env.cssdb.org/), lets you convert modern CSS into something most browsers can understand, determining the polyfills you need based on your targeted browsers or runtime environments, using [cssdb](https://cssdb.org/).

body {
  color: oklch(61% 0.2 29);
}

CSS input

body {
  color: rgb(225, 65, 52);
}

CSS output

[CSS Modules](https://github.com/css-modules/css-modules) means you never need to worry about your names being too generic, just use whatever makes the most sense.

.name {
  color: gray;
}

CSS input

.Logo\_\_name\_\_SVK0g {
  color: gray;
}

CSS output

Enforce consistent conventions and avoid errors in your stylesheets with [stylelint](https://stylelint.io/), a modern CSS linter. It supports the latest CSS syntax, as well as CSS-like syntaxes, such as SCSS.

a {
  color: #d3;
}

CSS input

app.css
2:10 Invalid hex color

Console output

*   [Setup](https://github.com/postcss/postcss#usage)
*   [Documentation](https://postcss.org/docs/)
*   [Learn](https://github.com/postcss/postcss#articles)
*   [Plugins](https://postcss.org/docs/postcss-plugins)
*   [Donate](https://opencollective.com/postcss/)

Trusted by industry leaders
---------------------------

*   ![Facebook](https://postcss.org/assets/facebook-K-cNuQBS.svg)
*   ![GitHub](https://postcss.org/assets/github-2Dp5HpE7.svg)
*   ![Google](https://postcss.org/assets/google-AcfcgM23.svg)
*   ![WordPress](https://postcss.org/assets/wordpress-vvrhDZG0.svg)
*   ![Wikipedia](https://postcss.org/assets/wikipedia-Ci2oqMXd.svg)
*   ![JetBrains](https://postcss.org/assets/jetbrains-CZbR3dQs.svg)
*   ![Taobao](https://postcss.org/assets/taobao-C_zl4NI4.svg)
