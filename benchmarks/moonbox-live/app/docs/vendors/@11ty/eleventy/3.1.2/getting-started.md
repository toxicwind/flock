Breadcrumbs:

*   [Eleventy Documentation](https://www.11ty.dev/docs/)
*   [Guide](https://www.11ty.dev/docs/projects/)

Get Started
-----------

Eleventy v3.1.2 requires a [JavaScript runtime](https://www.11ty.dev/docs/javascript-runtime/), usually **[Node.js](https://nodejs.org/)** — **version 18** or higher.

You can check whether or not you have Node.js installed by running `node --version` in a terminal application. ([_Well, wait—what is a Terminal?_](https://www.11ty.dev/docs/terminal-window/)) If the command is not found or it reports a number lower than 18, you will need to [download and install Node.js](https://nodejs.org/en/download/) before moving on to the next step. We encourage folks to use [even numbered releases](https://www.11ty.dev/docs/javascript-runtime/#odd-versions-of-node-js) of Node.js.

Prefer to watch videos instead? Check out [**6 minutes to Build a Blog from Scratch**](https://www.youtube.com/watch?v=kzf9A9tkkl4).

Step 1 Make a Project Directory
-------------------------------

Create a directory for your project using the `mkdir` command (short for _make directory_):

    mkdir eleventy-sample

Now move into that directory with the `cd` command (short for _change directory_):

    cd eleventy-sample

Step 2 Install Eleventy
-----------------------

### Create a `package.json`

Installing Eleventy into a project requires a `package.json` file.

    npm init -y

The `npm` command (included with Node.js) will create a `package.json` file for you with [`npm init -y`](https://docs.npmjs.com/cli/init). The `-y` flag tells `npm` to use default values and skips the questionnaire.

Use the following command if you want to use [ESM in your project and not CommonJS](https://www.11ty.dev/docs/cjs-esm/).

    npm pkg set type="module"

    pnpm init

Learn more about [pnpm](https://pnpm.io/) (it requires separate installation).

    yarn init

Learn more about [yarn](https://yarnpkg.com/) (it requires separate installation).

### Install Eleventy

[`@11ty/eleventy` is published on npm](https://www.npmjs.com/package/@11ty/eleventy) and we can install and save it into our project’s `package.json` by running:

    npm install @11ty/eleventy

    pnpm install @11ty/eleventy

    yarn add @11ty/eleventy

_You may also [install Eleventy globally](https://www.11ty.dev/docs/global-installation/) but the `package.json` installation method above is recommended._

Step 3 Run Eleventy
-------------------

    npx @11ty/eleventy

We can use the `npx` command (also provided by Node.js) to run our local project's version of Eleventy.

    pnpm exec eleventy

    yarn exec eleventy

Here’s what your command line might look like after you run Eleventy:

    [11ty] Wrote 0 files in 0.03 seconds (v3.1.2)

If you see `(v3.1.2)` in your output you know you’re using the newest version. However, Eleventy didn’t process any files! This is expected—we have an empty folder with no templates inside.

Step 4 Create some templates
----------------------------

A template is a content file written in a [format such as Markdown, HTML, Liquid, Nunjucks, and more](https://www.11ty.dev/docs/languages/), which Eleventy transforms into a page (or pages) when building our site.

Let’s run two commands to create two new template files.

    echo '<!doctype html><title>Page title</title><p>Hi</p>' > index.htmlecho '# Heading' > README.md

    echo '<!doctype html><title>Page title</title><p>Hi</p>' | out-file -encoding utf8 'index.html'echo '# Heading' | out-file -encoding utf8 'README.md'

If the `out-file` command is not available in your Windows Terminal window (it’s PowerShell specific), use the Cross Platform method instead.

    npx @11ty/create index.html "<!doctype html><title>Page title</title><p>Hi</p>"npx @11ty/create README.md "# Heading"

Learn more about [`@11ty/create`](https://github.com/11ty/create) _(requires Node.js 18 or newer)_.

Alternatively, you can create these using any text editor — make sure you save them into your project folder and they have the correct file extensions.

After you’ve created an HTML template and a Markdown template, let’s run Eleventy again with the following command:

    npx @11ty/eleventy

    pnpm exec eleventy

    yarn exec eleventy

The output might look like this:

    [11ty] Writing _site/README/index.html from ./README.md (liquid)[11ty] Writing _site/index.html from ./index.html (liquid)[11ty] Wrote 2 files in 0.04 seconds (v3.1.2)

We’ve now compiled our two content templates in the current directory into the output folder (`_site` is the default).

If you’d like to experiment further with [template file syntax](https://www.11ty.dev/docs/languages/), edit the following sample `README.md` file in your browser. [Front Matter](https://www.11ty.dev/docs/data-frontmatter/), [Liquid](https://www.11ty.dev/docs/languages/liquid/) and [Markdown](https://www.11ty.dev/docs/languages/markdown/) syntax are in use.

    ---title: Heading---# {{ title }}

Step 5 Gaze upon your templates
-------------------------------

Use `--serve` to start up a hot-reloading local web server.

    npx @11ty/eleventy --serve

    pnpm exec eleventy --serve

    yarn exec eleventy -- --serve

Your command line might look something like:

    [11ty] Writing _site/index.html from ./index.html (liquid)[11ty] Writing _site/README/index.html from ./README.md (liquid)[11ty] Wrote 2 files in 0.04 seconds (v3.1.2)[11ty] Watching…[11ty] Server at http://localhost:8080/

Open `http://localhost:8080/` or `http://localhost:8080/README/` in your favorite web browser to see your Eleventy site live! When you save your template files—Eleventy will refresh the browser with your new changes automatically!

Step 6 Put it online (optional)
-------------------------------

Your output folder (`_site`) now contains all of the statically built files for your new web site. You can upload this folder to any web host! Head over to our [deployment documentation](https://www.11ty.dev/docs/deployment/) to read more about putting your Eleventy project online for everyone to see.

Step 7 Continue Learning…
-------------------------

Congratulations—you made something with Eleventy! Now put it to work:

1.  Add more content! In the above tutorial we used [HTML](https://www.11ty.dev/docs/languages/html/) and [Markdown](https://www.11ty.dev/docs/languages/markdown/). Why not [JavaScript](https://www.11ty.dev/docs/languages/javascript/) or [WebC](https://www.11ty.dev/docs/languages/webc/) (for components) next? [Nunjucks](https://www.11ty.dev/docs/languages/nunjucks/) and [Liquid](https://www.11ty.dev/docs/languages/liquid/) are also very popular. Maybe you’re feeling super adventurous and want to [add your own custom type?](https://www.11ty.dev/docs/languages/custom/).
2.  Use [a layout file so that you don’t have to repeat boilerplate on every template](https://www.11ty.dev/docs/layouts/).
3.  Add a [configuration file](https://www.11ty.dev/docs/config/) to unlock advanced Eleventy capabilities!
4.  Add [CSS, JavaScript, or Web Fonts](https://www.11ty.dev/docs/assets/) to your project.
5.  It’s super easy to add automated [Image optimization](https://www.11ty.dev/docs/plugins/image/) too!
6.  Learn more of the [command line options for Eleventy](https://www.11ty.dev/docs/usage/).
7.  Perhaps you’d like to [consume data from third party APIs](https://www.11ty.dev/docs/data-js/) in your project?

### Tutorials and Starter Projects

For folks wanting to **build a blog**, you can learn how to [start from scratch](https://www.youtube.com/watch?v=kzf9A9tkkl4) _(learn how it works)_ or use our [official Blog starter project](https://github.com/11ty/eleventy-base-blog) _(get up and running faster)_:

You can also use one of the many [**Starter Projects**](https://www.11ty.dev/docs/starter/) or read some of our excellent Community-contributed [**Tutorials**](https://www.11ty.dev/docs/tutorials/) (a curated few of which are included below):

×99 resources via **[11tybundle.dev](https://11tybundle.dev/)** curated by [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.bobmonsour.com%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.bobmonsour.com%2F/)Bob Monsour](https://www.bobmonsour.com/).

**_Expand to see 94 more resources._**

*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2F32x33.institute%2Fhost-your-stuff-part-vi%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2F32x33.institute%2Fhost-your-stuff-part-vi%2F/)Host Your Stuff](https://32x33.institute/host-your-stuff-part-vi/) — _Scarlett Cavendish (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.adamdjbrett.com%2Fblog%2F2025-02-23-get-tufte%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.adamdjbrett.com%2Fblog%2F2025-02-23-get-tufte%2F/)Embracing Tufte’s Design Principles in My New 11ty Starter](https://www.adamdjbrett.com/blog/2025-02-23-get-tufte/) — _Adam DJ Brett (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.adamdjbrett.com%2Fblog%2F2025-02-22-brutalism-eleventy-web-design%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.adamdjbrett.com%2Fblog%2F2025-02-22-brutalism-eleventy-web-design%2F/)My (Neo)Brutalism 11ty Web Design Experiments](https://www.adamdjbrett.com/blog/2025-02-22-brutalism-eleventy-web-design/) — _Adam DJ Brett (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.chobble.com%2Fblog%2F25-03-28-chobble-template%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.chobble.com%2Fblog%2F25-03-28-chobble-template%2F/)Introducing the "Chobble Template"](https://blog.chobble.com/blog/25-03-28-chobble-template/) — _Stefan Burke (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.adamdjbrett.com%2Fblog%2F2025-02-21-my-tiny-11ty-sites%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.adamdjbrett.com%2Fblog%2F2025-02-21-my-tiny-11ty-sites%2F/)My Tiny Eleventy (11ty) Sites](https://www.adamdjbrett.com/blog/2025-02-21-my-tiny-11ty-sites/) — _Adam DJ Brett (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fnoscript.show%2Fbuild%2F7/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fnoscript.show%2Fbuild%2F7/)Building with an 11ty starter sites and headless WordPress](https://noscript.show/build/7) — _David Waumsley (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fabdullahyahya.com%2F2025%2F02%2Fset-up-a-simple-and-reliable-static-site-generator-using-11ty-eleventy-tailwind-css%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fabdullahyahya.com%2F2025%2F02%2Fset-up-a-simple-and-reliable-static-site-generator-using-11ty-eleventy-tailwind-css%2F/)Set Up a Simple and Reliable Static Site Generator Using 11ty (Eleventy) + Tailwind CSS](https://abdullahyahya.com/2025/02/set-up-a-simple-and-reliable-static-site-generator-using-11ty-eleventy-tailwind-css/) — _Abdullah Yahya (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DSTOvNBFQjnc/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DSTOvNBFQjnc/)Getting Started with 11ty, Minimalist, and Calavera](https://www.youtube.com/watch?v=STOvNBFQjnc) — _Schalk Neethling (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DIxxszvj9GKw/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DIxxszvj9GKw/)Long-term WordPress user tries building with 11ty](https://www.youtube.com/watch?v=Ixxszvj9GKw) — _David Waumsley (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fheterl0.live%2Fblog%2Fbuild-personal-blog-with-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fheterl0.live%2Fblog%2Fbuild-personal-blog-with-eleventy%2F/)Build personal blog easy with 11ty.js](https://heterl0.live/blog/build-personal-blog-with-eleventy/) — _Hieu Le Van (2025)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DKY9B90-nmgk/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DKY9B90-nmgk/)Let's Build a Blog Like it's 1990 - Part 2](https://www.youtube.com/watch?v=KY9B90-nmgk) — _Raymond Camden (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fgithub.com%2Fjeromecoupe%2Fiad_eleventy_introduction%2Fblob%2Fmaster%2Feleventy_introduction_en.md%23eleventy-11ty-by-zach-leatherman/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fgithub.com%2Fjeromecoupe%2Fiad_eleventy_introduction%2Fblob%2Fmaster%2Feleventy_introduction_en.md%23eleventy-11ty-by-zach-leatherman/)Eleventy Introduction](https://github.com/jeromecoupe/iad_eleventy_introduction/blob/master/eleventy_introduction_en.md#eleventy-11ty-by-zach-leatherman) — _Jérôme Coupé (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.htmlcenter.com%2Fblog%2Fbuild-static-website-with-11ty-part-2%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.htmlcenter.com%2Fblog%2Fbuild-static-website-with-11ty-part-2%2F/)Build static website with 11ty. Part 2](https://www.htmlcenter.com/blog/build-static-website-with-11ty-part-2/) — _ProDeveloper (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.htmlcenter.com%2Fblog%2Fhow-to-build-static-website-with-11ty%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.htmlcenter.com%2Fblog%2Fhow-to-build-static-website-with-11ty%2F/)How to build static website with 11ty](https://www.htmlcenter.com/blog/how-to-build-static-website-with-11ty/) — _ProDeveloper (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dt5lfwd5KScM%23t%3D14m47s/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dt5lfwd5KScM%23t%3D14m47s/)Let's Build a Blog Like it's 1990 - Part 1](https://www.youtube.com/watch?v=t5lfwd5KScM#t=14m47s) — _Raymond Camden (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.sebin-nyshkim.net%2Fposts%2Fbuilding-a-blog-with-eleventy-blind-any%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.sebin-nyshkim.net%2Fposts%2Fbuilding-a-blog-with-eleventy-blind-any%2F/)Building a Blog with Eleventy (blind, any%)](https://blog.sebin-nyshkim.net/posts/building-a-blog-with-eleventy-blind-any/) — _Sebin Nyshkim (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fhow-i-teach-eleventy-from-scratch%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fhow-i-teach-eleventy-from-scratch%2F/)How I teach Eleventy from scratch](https://hamatti.org/posts/how-i-teach-eleventy-from-scratch/) — _Juha-Matti Santala (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fgkeenan.co%2Favgb%2Fan-alarmingly-concise-and-very-hinged-summary-of-what-it-was-like-to-build-this-site-from-scratch%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fgkeenan.co%2Favgb%2Fan-alarmingly-concise-and-very-hinged-summary-of-what-it-was-like-to-build-this-site-from-scratch%2F/)An alarmingly concise and very hinged summary of what it was like to build this site from scratch](https://gkeenan.co/avgb/an-alarmingly-concise-and-very-hinged-summary-of-what-it-was-like-to-build-this-site-from-scratch/) — _Keenan (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.zachleat.com%2Fweb%2Fsmorgasbord-windows-terminal%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.zachleat.com%2Fweb%2Fsmorgasbord-windows-terminal%2F/)THE SMORGASBORD OF WINDOWS TERMINAL… WINDOWS](https://www.zachleat.com/web/smorgasbord-windows-terminal/) — _Zach Leatherman (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Feleventy-excellent.netlify.app%2Fblog%2Feleventy-excellent-30%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Feleventy-excellent.netlify.app%2Fblog%2Feleventy-excellent-30%2F/)Eleventy Excellent 3.0](https://eleventy-excellent.netlify.app/blog/eleventy-excellent-30/) — _Lene Saile (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.seanmcp.com%2Fgardens%2Fgetting-started-with-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.seanmcp.com%2Fgardens%2Fgetting-started-with-eleventy%2F/)Getting started with Eleventy](https://www.seanmcp.com/gardens/getting-started-with-eleventy/) — _Sean McPherson (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DyCF9l4_E5rI/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DyCF9l4_E5rI/)Curso Eleventy (Spanish video)](https://www.youtube.com/watch?v=yCF9l4_E5rI) — _Jon Mircha (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.logrocket.com%2Feleventy-adoption-guide%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.logrocket.com%2Feleventy-adoption-guide%2F/)Eleventy adoption guide: Overview, examples, and alternatives](https://blog.logrocket.com/eleventy-adoption-guide/) — _Nelson Michael (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.jetbrains.com%2Fguide%2Fjavascript%2Ftutorials%2Feleventy-tsx%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.jetbrains.com%2Fguide%2Fjavascript%2Ftutorials%2Feleventy-tsx%2F/)Better 11ty Development with Tooling](https://www.jetbrains.com/guide/javascript/tutorials/eleventy-tsx/) — _Paul Everitt (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Findex-md-is-valid-eleventy-project%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Findex-md-is-valid-eleventy-project%2F/)index.md is a valid Eleventy project](https://hamatti.org/posts/index-md-is-valid-eleventy-project/) — _Juha-Matti Santala (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fw3things.com%2Fblog%2Feleventy-tutorial%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fw3things.com%2Fblog%2Feleventy-tutorial%2F/)Eleventy Tutorial - Create an 11ty Static Site](https://w3things.com/blog/eleventy-tutorial/) — _Danial Zahid (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdaught.me%2Fblog%2F2024%2Findie-web%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdaught.me%2Fblog%2F2024%2Findie-web%2F/)The "IndieWeb" feels like coming home](https://daught.me/blog/2024/indie-web/) — _Nathaniel Daught (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fanhvn.com%2Fposts%2F2024%2Fmy-eleventy-site-setup%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fanhvn.com%2Fposts%2F2024%2Fmy-eleventy-site-setup%2F/)My Eleventy site setup](https://anhvn.com/posts/2024/my-eleventy-site-setup/) — _anh (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcss-irl.info%2Feleventy-starter-projects-updates%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcss-irl.info%2Feleventy-starter-projects-updates%2F/)CSS { In Real Life } | Eleventy Starter Project Updates](https://css-irl.info/eleventy-starter-projects-updates/) — _Michelle Barker (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2Ftop-11-free-eleventy-themes-for-2024%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2Ftop-11-free-eleventy-themes-for-2024%2F/)Top 11 free Eleventy themes for 2024](https://cloudcannon.com/blog/top-11-free-eleventy-themes-for-2024/) — _Jaimie McMahon (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.njfamirm.ir%2Fen%2Fblog%2Feleventy-folder-structure-guide%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.njfamirm.ir%2Fen%2Fblog%2Feleventy-folder-structure-guide%2F/)Mastering Eleventy Folder Structures: From Default Setups to Real-World Best Practices](https://www.njfamirm.ir/en/blog/eleventy-folder-structure-guide/) — _S. Amir Mohammad Najafi (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DtzZ_gRhefbs/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DtzZ_gRhefbs/)From Figma to Browser with Eleventy (Part 3)](https://www.youtube.com/watch?v=tzZ_gRhefbs) — _thoughtbot (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fthenewstack.io%2Fintroduction-to-eleventy-a-modern-static-website-generator%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fthenewstack.io%2Fintroduction-to-eleventy-a-modern-static-website-generator%2F/)Introduction to Eleventy, a Modern Static Website Generator](https://thenewstack.io/introduction-to-eleventy-a-modern-static-website-generator/) — _David Eastman (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.learnwithgurpreet.com%2Fposts%2Feleventy-resume-builder%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.learnwithgurpreet.com%2Fposts%2Feleventy-resume-builder%2F/)Eleventy Resume Builder](https://www.learnwithgurpreet.com/posts/eleventy-resume-builder/) — _Gurpreet Singh (2024)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.logrocket.com%2Feleventy-vs-next-js-static-site-generation%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fblog.logrocket.com%2Feleventy-vs-next-js-static-site-generation%2F/)Eleventy vs. Next.js for static site generation](https://blog.logrocket.com/eleventy-vs-next-js-static-site-generation/) — _Nelson Michael (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dlnu7ytQuF0k/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dlnu7ytQuF0k/)Implementing a Figma design in Eleventy (Part 2)](https://www.youtube.com/watch?v=lnu7ytQuF0k) — _thoughtbot (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Frenkotsuban.neocities.org%2Fposts%2F2023-11-15-Migrating-to-Eleventy/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Frenkotsuban.neocities.org%2Fposts%2F2023-11-15-Migrating-to-Eleventy/)Migrating to Eleventy](https://renkotsuban.neocities.org/posts/2023-11-15-Migrating-to-Eleventy) — _Renkon (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DN9fIzgvIl0Q%26t%3D12s/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DN9fIzgvIl0Q%26t%3D12s/)From Figma to Browser with Eleventy (Part 1)](https://www.youtube.com/watch?v=N9fIzgvIl0Q&t=12s) — _thoughtbot (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwhiona.weblog.lol%2F2023%2F10%2Fmy-neocities-workflow%3A-using-eleventy-and-the-cli-to-speed-up-development/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwhiona.weblog.lol%2F2023%2F10%2Fmy-neocities-workflow%3A-using-eleventy-and-the-cli-to-speed-up-development/)My Neocities workflow: using Eleventy and the CLI to speed up development](https://whiona.weblog.lol/2023/10/my-neocities-workflow:-using-eleventy-and-the-cli-to-speed-up-development) — _Whiona (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.simoncox.com%2Fblog%2F2023-08-05-build-your-own-11ty-starter%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.simoncox.com%2Fblog%2F2023-08-05-build-your-own-11ty-starter%2F/)Build your own 11ty starter](https://www.simoncox.com/blog/2023-08-05-build-your-own-11ty-starter/) — _Simon Cox (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.webiny.com%2Fblog%2Fbuild-blog-eleventy-webiny-headless-cms/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.webiny.com%2Fblog%2Fbuild-blog-eleventy-webiny-headless-cms/)Build a Blog with Eleventy (11ty) and Webiny Headless CMS](https://www.webiny.com/blog/build-blog-eleventy-webiny-headless-cms) — _Maurice King (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fdocumentation%2Fguides%2Fbookshop-eleventy-guide%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fdocumentation%2Fguides%2Fbookshop-eleventy-guide%2F/)Bookshop 11ty Guide](https://cloudcannon.com/documentation/guides/bookshop-eleventy-guide/) — _CloudCannon (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fequk.co.uk%2F2023%2F06%2F10%2Fblog-using-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fequk.co.uk%2F2023%2F06%2F10%2Fblog-using-eleventy%2F/)Blog Using Eleventy](https://equk.co.uk/2023/06/10/blog-using-eleventy/) — _equilibriumuk (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raymondcamden.com%2F2023%2F05%2F18%2Feleventy-by-example-by-bryan-robinson/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raymondcamden.com%2F2023%2F05%2F18%2Feleventy-by-example-by-bryan-robinson/)Eleventy by Example, by Bryan Robinson](https://www.raymondcamden.com/2023/05/18/eleventy-by-example-by-bryan-robinson) — _Raymond Camden (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Ffullstackdigital.io%2Fblog%2Feleventy-vite-tailwind-and-alpine-js-rapid-static-site-starter-framework%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Ffullstackdigital.io%2Fblog%2Feleventy-vite-tailwind-and-alpine-js-rapid-static-site-starter-framework%2F/)Eleventy (11ty), Vite, Tailwind, and Alpine.js – Rapid static site starter framework](https://fullstackdigital.io/blog/eleventy-vite-tailwind-and-alpine-js-rapid-static-site-starter-framework/) — _Full Stack Digital (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fbryanlrobinson.com%2Fblog%2Fbook-release-eleventy-by-example-learn-11ty-with-5-in-depth-projects%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fbryanlrobinson.com%2Fblog%2Fbook-release-eleventy-by-example-learn-11ty-with-5-in-depth-projects%2F/)Book Release: Eleventy by Example – Learn 11ty with 5 in-depth projects](https://bryanlrobinson.com/blog/book-release-eleventy-by-example-learn-11ty-with-5-in-depth-projects/) — _Bryan Robinson (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fkinsta.com%2Fblog%2Feleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fkinsta.com%2Fblog%2Feleventy%2F/)How To Craft a Stylish Static Website with Eleventy (11ty)](https://kinsta.com/blog/eleventy/) — _Joel Olawanle (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcfjedimaster.github.io%2Feleventy-blog-guide%2Fguide.html/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcfjedimaster.github.io%2Feleventy-blog-guide%2Fguide.html/)A Complete Guide to Building a Blog with Eleventy](https://cfjedimaster.github.io/eleventy-blog-guide/guide.html) — _Raymond Camden (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D71q-C9BVUng/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D71q-C9BVUng/)Eleventy - Build a Static Site with Backend Data Handling - YouTube](https://www.youtube.com/watch?v=71q-C9BVUng) — _Azul Coding (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raymondcamden.com%2F2023%2F02%2F25%2Fupdate-to-my-eleventy-blog-guide/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raymondcamden.com%2F2023%2F02%2F25%2Fupdate-to-my-eleventy-blog-guide/)Update to My Eleventy Blog Guide](https://www.raymondcamden.com/2023/02/25/update-to-my-eleventy-blog-guide) — _Raymond Camden (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fsombriks.com%2Fblog%2F0042-getting-started-with-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fsombriks.com%2Fblog%2F0042-getting-started-with-eleventy%2F/)Getting started with eleventy](https://sombriks.com/blog/0042-getting-started-with-eleventy/) — _Leonardo Silveira (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fjakubiwanowski.dev%2Fgarden%2Fprogramming%2Feleventy-guide-part-two%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fjakubiwanowski.dev%2Fgarden%2Fprogramming%2Feleventy-guide-part-two%2F/)A Beginner's Guide to Eleventy - part two](https://jakubiwanowski.dev/garden/programming/eleventy-guide-part-two/) — _Jakub Iwanowski (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fjakubiwanowski.dev%2Fgarden%2Fprogramming%2Feleventy-guide-part-one%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fjakubiwanowski.dev%2Fgarden%2Fprogramming%2Feleventy-guide-part-one%2F/)A Beginner's Guide to Eleventy - part one](https://jakubiwanowski.dev/garden/programming/eleventy-guide-part-one/) — _Jakub Iwanowski (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2F23-of-the-best-eleventy-themes-for-2023%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2F23-of-the-best-eleventy-themes-for-2023%2F/)23 of the best Eleventy Themes (Starters) for 2023](https://cloudcannon.com/blog/23-of-the-best-eleventy-themes-for-2023/) — _David Large (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Ftiiny.host%2Fblog%2Fintroductory-guide-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Ftiiny.host%2Fblog%2Fintroductory-guide-eleventy%2F/)An Introductory Guide to Eleventy](https://tiiny.host/blog/introductory-guide-eleventy/) — _Don Hamilton (2023)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2F11-top-eleventy-blog-themes-starters-in-2023%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2F11-top-eleventy-blog-themes-starters-in-2023%2F/)11 Top Eleventy Blog Themes (Starters) in 2023](https://cloudcannon.com/blog/11-top-eleventy-blog-themes-starters-in-2023/) — _David Large (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2Fnew-eleventy-features-a-new-theme-and-full-eleventy-support%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Fblog%2Fnew-eleventy-features-a-new-theme-and-full-eleventy-support%2F/)New Eleventy features, a new theme, and full Eleventy support](https://cloudcannon.com/blog/new-eleventy-features-a-new-theme-and-full-eleventy-support/) — _CloudCannon (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdustinwhisman.com%2Fwriting%2Feleventy-starter-template%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdustinwhisman.com%2Fwriting%2Feleventy-starter-template%2F/)Eleventy Starter Template Series](https://dustinwhisman.com/writing/eleventy-starter-template/) — _Dustin Whisman (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fsparkbox.com%2Ffoundry%2Fseries%2Fbuilding_an_eleventy_starter_template/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fsparkbox.com%2Ffoundry%2Fseries%2Fbuilding_an_eleventy_starter_template/)Building an Eleventy Starter Template Series](https://sparkbox.com/foundry/series/building_an_eleventy_starter_template) — _Dustin Whisman (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Ftutorials%2Feleventy-beginner-tutorial%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcloudcannon.com%2Ftutorials%2Feleventy-beginner-tutorial%2F/)Getting set up in Eleventy (6 part series)](https://cloudcannon.com/tutorials/eleventy-beginner-tutorial/) — _Mike Neumegen (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.freecodecamp.org%2Fnews%2Flearn-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.freecodecamp.org%2Fnews%2Flearn-eleventy%2F/)Learn the Eleventy Static Site Generator by Building and Deploying a Portfolio Website](https://www.freecodecamp.org/news/learn-eleventy/) — _Gerard Hynes (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fgarage.sekrab.com%2Fposts%2Fwalk-with-an-eleventy-site-before-you-can-run/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fgarage.sekrab.com%2Fposts%2Fwalk-with-an-eleventy-site-before-you-can-run/)Walk with an Eleventy site, before you can run](https://garage.sekrab.com/posts/walk-with-an-eleventy-site-before-you-can-run) — _Amal Ayyash (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fplaylist%3Flist%3DPLtLXFsdHI8JTwScHvB924dY3PNwNJjjuW/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fplaylist%3Flist%3DPLtLXFsdHI8JTwScHvB924dY3PNwNJjjuW/)Eleventy Crash Course - YouTube playlist](https://www.youtube.com/playlist?list=PLtLXFsdHI8JTwScHvB924dY3PNwNJjjuW) — _Jaydan Urwin (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fpsypher1%2Flets-learn-eleventy-1a67/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fpsypher1%2Flets-learn-eleventy-1a67/)Let's Learn Eleventy (11 Part Series)](https://dev.to/psypher1/lets-learn-eleventy-1a67) — _James Midzi (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdesign2seo.com%2Fblog%2Fweb-development%2F11ty%2Fbuild-a-blog-with-11ty-part-3%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdesign2seo.com%2Fblog%2Fweb-development%2F11ty%2Fbuild-a-blog-with-11ty-part-3%2F/)Build a Blog With 11ty: Categories - Part 3](https://design2seo.com/blog/web-development/11ty/build-a-blog-with-11ty-part-3/) — _Jeremy Faucher (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdesign2seo.com%2Fblog%2Fweb-development%2F11ty%2Fbuild-a-blog-with-11ty-part-2%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdesign2seo.com%2Fblog%2Fweb-development%2F11ty%2Fbuild-a-blog-with-11ty-part-2%2F/)Build a Blog With 11ty: Base - Part 2](https://design2seo.com/blog/web-development/11ty/build-a-blog-with-11ty-part-2/) — _Jeremy Faucher (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdesign2seo.com%2Fblog%2Fweb-development%2F11ty%2Fbuild-a-blog-with-11ty-part-1%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdesign2seo.com%2Fblog%2Fweb-development%2F11ty%2Fbuild-a-blog-with-11ty-part-1%2F/)Build a Blog With 11ty: Setup - Part 1](https://design2seo.com/blog/web-development/11ty/build-a-blog-with-11ty-part-1/) — _Jeremy Faucher (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdustinwhisman.com%2Fwriting%2Feleventy-starter-template%2Fintro%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdustinwhisman.com%2Fwriting%2Feleventy-starter-template%2Fintro%2F/)Setting up Future Projects for Success with Template Repositories](https://dustinwhisman.com/writing/eleventy-starter-template/intro/) — _Dustin Whisman (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fthinkdobecreate.com%2Farticles%2Fminimum-static-site-sass-setup%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fthinkdobecreate.com%2Farticles%2Fminimum-static-site-sass-setup%2F/)Minimum Static Site Setup with Sass](https://thinkdobecreate.com/articles/minimum-static-site-sass-setup/) — _Stephanie Eckles (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raymondcamden.com%2F2022%2F01%2F19%2Fa-guide-to-building-a-blog-in-eleventy/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raymondcamden.com%2F2022%2F01%2F19%2Fa-guide-to-building-a-blog-in-eleventy/)A Guide to Building a Blog in Eleventy](https://www.raymondcamden.com/2022/01/19/a-guide-to-building-a-blog-in-eleventy) — _Raymond Camden (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwebpixels.io%2Fblog%2Fhow-to-get-started-with-bootstrap-and-eleventy/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwebpixels.io%2Fblog%2Fhow-to-get-started-with-bootstrap-and-eleventy/)Build JAMstack-ready sites with Bootstrap and 11ty (Eleventy)](https://webpixels.io/blog/how-to-get-started-with-bootstrap-and-eleventy) — _Webpixels (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdavidea.st%2Farticles%2F11ty-tips-i-wish-i-knew-from-the-start%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdavidea.st%2Farticles%2F11ty-tips-i-wish-i-knew-from-the-start%2F/)11ty tips I wish I knew from the start](https://davidea.st/articles/11ty-tips-i-wish-i-knew-from-the-start/) — _David East (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.tim-kleyersburg.de%2Farticles%2Feleventyjs-is-great%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.tim-kleyersburg.de%2Farticles%2Feleventyjs-is-great%2F/)Going all in with Jamstack and Eleventy](https://www.tim-kleyersburg.de/articles/eleventyjs-is-great/) — _Tim Kleyersburg (2022)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fkeenanpayne.com%2F11ty-eleventy-introduction%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fkeenanpayne.com%2F11ty-eleventy-introduction%2F/)Introduction to Eleventy (11ty) ELEVENTY](https://keenanpayne.com/11ty-eleventy-introduction/) — _Keenan Payne (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhelloyes.dev%2Fblog%2F2021%2Felventy-should-be-next%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhelloyes.dev%2Fblog%2F2021%2Felventy-should-be-next%2F/)Make Eleventy the next thing you learn](https://helloyes.dev/blog/2021/elventy-should-be-next/) — _Thomas Semmler (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fngblaylock%2Fhow-i-set-up-a-project-with-eleventy-31gc/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fngblaylock%2Fhow-i-set-up-a-project-with-eleventy-31gc/)How I Set Up a Project With Eleventy](https://dev.to/ngblaylock/how-i-set-up-a-project-with-eleventy-31gc) — _Nathan Blaylock (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D4wD00RT6d-g/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D4wD00RT6d-g/)Turn static HTML/CSS into a blog with CMS using the JAMStack](https://www.youtube.com/watch?v=4wD00RT6d-g) — _Kevin Powell (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fsia.codes%2Fposts%2Fitsiest-bitsiest-eleventy-tutorial%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fsia.codes%2Fposts%2Fitsiest-bitsiest-eleventy-tutorial%2F/)Itsiest, Bitsiest Eleventy Tutorial](https://sia.codes/posts/itsiest-bitsiest-eleventy-tutorial/) — _Sia Karamalegos (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2F11ty.rocks%2Fposts%2Fdeep-dive-eleventy-static-site-generator%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2F11ty.rocks%2Fposts%2Fdeep-dive-eleventy-static-site-generator%2F/)A Deep Dive Into Eleventy Static Site Generator](https://11ty.rocks/posts/deep-dive-eleventy-static-site-generator/) — _Stephanie Eckles (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fingosteinke%2Fcreating-a-fast-and-beautiful-portfolio-website-using-html-css-and-eleventy-and-netlify-9f5/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fingosteinke%2Fcreating-a-fast-and-beautiful-portfolio-website-using-html-css-and-eleventy-and-netlify-9f5/)Creating a Fast and Beautiful Portfolio Website using HTML, CSS, Eleventy and Netlify](https://dev.to/ingosteinke/creating-a-fast-and-beautiful-portfolio-website-using-html-css-and-eleventy-and-netlify-9f5) — _Ingo Steinke (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fstudio_m_song%2Feleventy-in-eleven-minutes-2mno/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Fstudio_m_song%2Feleventy-in-eleven-minutes-2mno/)Eleventy in eleven minutes](https://dev.to/studio_m_song/eleventy-in-eleven-minutes-2mno) — _Lea Rosema (2021)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fmichaelharley.net%2Fposts%2F2020%2F12%2F20%2Fbuilding-my-personal-site-with-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fmichaelharley.net%2Fposts%2F2020%2F12%2F20%2Fbuilding-my-personal-site-with-eleventy%2F/)Building my personal site with Eleventy](https://michaelharley.net/posts/2020/12/20/building-my-personal-site-with-eleventy/) — _Michael Harley (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcfe.dev%2Fevents%2Fjamstack-101-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fcfe.dev%2Fevents%2Fjamstack-101-eleventy%2F/)Jamstack 101: Getting Started with Eleventy](https://cfe.dev/events/jamstack-101-eleventy/) — _Joel Varty (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Floige%2Fgetting-started-with-eleventy-in-11-minutes-496j/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fdev.to%2Floige%2Fgetting-started-with-eleventy-in-11-minutes-496j/)Getting started with Eleventy in 11 minutes](https://dev.to/loige/getting-started-with-eleventy-in-11-minutes-496j) — _Luciano Mammino (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raresportan.com%2Feleventy-part-one%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.raresportan.com%2Feleventy-part-one%2F/)Let's Learn Eleventy (11ty) - What is Eleventy?](https://www.raresportan.com/eleventy-part-one/) — _Rares Portan (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.netlify.com%2Fblog%2F2020%2F04%2F09%2Flets-learn-eleventy-boost-your-jamstack-skills-with-11ty%2F%23main/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.netlify.com%2Fblog%2F2020%2F04%2F09%2Flets-learn-eleventy-boost-your-jamstack-skills-with-11ty%2F%23main/)Let’s Learn Eleventy! Boost your Jamstack skills with 11ty](https://www.netlify.com/blog/2020/04/09/lets-learn-eleventy-boost-your-jamstack-skills-with-11ty/#main) — _Jason Lengstorf (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fkhalidabuhakmeh.com%2Ffive-critical-things-before-working-with-11ty/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fkhalidabuhakmeh.com%2Ffive-critical-things-before-working-with-11ty/)Five Critical Things To Do Before Working With 11ty](https://khalidabuhakmeh.com/five-critical-things-before-working-with-11ty) — _Khalid Abuhakmeh (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fbuilding-a-website-with-a-static-site-generator-part-3-domain-analytics-and-forms%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fbuilding-a-website-with-a-static-site-generator-part-3-domain-analytics-and-forms%2F/)Building a website with a static site generator, part 3: Domain, Analytics and Forms](https://hamatti.org/posts/building-a-website-with-a-static-site-generator-part-3-domain-analytics-and-forms/) — _Juha-Matti Santala (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fbuilding-a-website-with-a-static-site-generator-part-2-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fbuilding-a-website-with-a-static-site-generator-part-2-eleventy%2F/)Building a website with a static site generator, part 2: Eleventy](https://hamatti.org/posts/building-a-website-with-a-static-site-generator-part-2-eleventy/) — _Juha-Matti Santala (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fbuilding-a-website-with-a-static-site-generator-part-1%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fhamatti.org%2Fposts%2Fbuilding-a-website-with-a-static-site-generator-part-1%2F/)Building a website with a static site generator, part 1: Setup](https://hamatti.org/posts/building-a-website-with-a-static-site-generator-part-1/) — _Juha-Matti Santala (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Frphunt.github.io%2Feleventy-walkthrough%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Frphunt.github.io%2Feleventy-walkthrough%2F/)Eleventy Walkthrough](https://rphunt.github.io/eleventy-walkthrough/) — _Reg Hunt (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.webstoemp.com%2Fblog%2Fteaching-eleventy%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.webstoemp.com%2Fblog%2Fteaching-eleventy%2F/)Teaching in the open: Eleventy](https://www.webstoemp.com/blog/teaching-eleventy/) — _Jérôme Coupé (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dj8mJrhhdHWc/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dj8mJrhhdHWc/)Let’s Learn Eleventy!](https://www.youtube.com/watch?v=j8mJrhhdHWc) — _Zach Leatherman (2020)_
*   [![IndieWeb Avatar for https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.filamentgroup.com%2Flab%2Fbuild-a-blog%2F/](https://v1.indieweb-avatar.11ty.dev/https%3A%2F%2Fwww.filamentgroup.com%2Flab%2Fbuild-a-blog%2F/)Build your own Blog from Scratch using Eleventy](https://www.filamentgroup.com/lab/build-a-blog/) — _Zach Leatherman (2018)_

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
