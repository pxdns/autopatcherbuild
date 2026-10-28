#!/usr/bin/env python3
"""Writes every page of the static site into site/. Run from the repo root: python3 tools/gen_site.py
Text comes from NOTICE.md and LICENSE-EXCEPTION.txt; keep them in step when either changes."""
import os

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
UPDATED = "28 October 2026"
REPO = "https://github.com/pxdns/autopatcherbuild"

NAV = [("index.html", "Home"), ("versions.html", "Versions"), ("guide.html", "Guide"),
       ("credits.html", "Credits"), ("legal.html", "Legal")]
LEGAL = [("legal.html", "Overview"), ("licence.html", "Licence"), ("dmca.html", "Copyright / DMCA"),
         ("privacy.html", "Privacy")]


def page(fn, title, desc, body, active, legal=False):
    nav = "".join('<a class="l" href="%s"%s>%s</a>' % (h, ' aria-current="page"' if (h == active or (legal and h == "legal.html")) else "", t) for h, t in NAV)
    sub = ""
    if legal:
        sub = '<nav class="subnav" aria-label="Legal pages">' + "".join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == active else "", t) for h, t in LEGAL) + "</nav>"
    html = f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="stylesheet" href="style.css">
</head><body>
<header><div class="bar"><a class="brand" href="index.html"><img src="img/icon.png" alt=""><span>Autopatcher</span></a>{nav}<button class="theme" id="theme" type="button">Dark theme</button></div></header>
<main>
{sub}{body}
</main>
<footer><div class="in"><span>Created by murd.er. Not affiliated with Mojang or Microsoft. Minecraft is a trademark of Mojang Studios.</span><span><a href="credits.html">Credits</a> &middot; <a href="licence.html">Licence</a> &middot; <a href="dmca.html">Copyright / DMCA</a> &middot; <a href="privacy.html">Privacy</a> &middot; <a href="{REPO}">Source</a></span></div></footer>
<script src="app.js"></script>
</body></html>
'''
    with open(os.path.join(SITE, fn), "w", encoding="utf-8") as f:
        f.write(html)


status = '<div class="status"><span class="dot" id="dot"></span><span id="status-text">Checking build status&hellip;</span></div>'

# ---------------------------------------------------------------- home
page("index.html", "Autopatcher", "Pick a Minecraft version, download its patcher, and run it with your own official client jar.", f'''
<section class="intro">
<div class="eyebrow">Eaglercraft patchers</div>
<h1>Build a browser client from your own Minecraft jar</h1>
<p class="lead">Pick a version, download its patcher, and run it with your own official client jar. The jar is never included and never uploaded.</p>
<div class="row"><a class="btn" href="versions.html">Choose a version</a><a class="btn ghost" href="guide.html">Read the guide</a></div>
</section>
{status}
<div class="cols">
<div class="box"><h3>Bring your own jar</h3><p>You supply the official client for your version. Nothing from Mojang is hosted here.</p></div>
<div class="box"><h3>Small package</h3><p>Each release holds only the patcher. It builds the client on your machine.</p></div>
<div class="box"><h3>Page or project</h3><p>Build a standalone page, or a source project to keep working on.</p></div>
</div>
<h2>Latest versions</h2>
<div id="list" data-limit="3"></div>
<p style="margin-top:14px"><a href="versions.html">All versions &rarr;</a></p>
''', "index.html")

# ---------------------------------------------------------------- versions
page("versions.html", "Versions &middot; Autopatcher", "Every Minecraft version and where its patcher stands.", f'''
<section class="intro"><div class="eyebrow">Versions</div><h1>Choose a version</h1>
<p class="lead" style="margin:0">Only versions marked ready can be downloaded.</p></section>
{status}
<div id="list"></div>
''', "versions.html")

# ---------------------------------------------------------------- guide
page("guide.html", "Guide &middot; Autopatcher", "How to run a patcher with your own client jar.", '''
<section class="intro"><div class="eyebrow">Guide</div><h1>How to use it</h1>
<p class="lead" style="margin:0">Four steps, on any computer with Java 17 or newer.</p></section>
<ol class="steps">
<li><div class="c"><b>Download</b><span>Open <a href="versions.html">Versions</a> and download the patcher for your version.</span></div></li>
<li><div class="c"><b>Run it</b><span>Start it with the command below. Check your Java with <code>java -version</code>.</span></div></li>
<li><div class="c"><b>Choose your jar</b><span>Point it at your own official client jar for that version. You need a copy of the game you are allowed to use.</span></div></li>
<li><div class="c"><b>Build</b><span>Build a standalone page or a source project from the same run. Everything is made on your machine.</span></div></li>
</ol>
<h2>Command</h2>
<pre>java -jar Eaglercraft-&lt;version&gt;-patcher-cli.jar</pre>
<h2>Before you share what you build</h2>
<p>A client you generate contains Minecraft's code and files. Keep it for your own use unless you have the right to distribute it. See <a href="legal.html">Legal</a>.</p>
''', "guide.html")

# ---------------------------------------------------------------- credits
page("credits.html", "Credits &middot; Autopatcher", "Who made Autopatcher and the projects it builds on.", '''
<section class="intro"><div class="eyebrow">Credits</div><h1>Credits</h1>
<p class="lead" style="margin:0">Autopatcher was created by <b>murd.er</b>. It stands on other people's work, listed below.</p></section>

<h2>Creator</h2>
<dl class="facts">
<dt>Created by</dt><dd>murd.er</dd>
<dt>Source</dt><dd><a href="https://github.com/pxdns/autopatcherbuild">github.com/pxdns/autopatcherbuild</a></dd>
<dt>Idea</dt><dd>The &ldquo;download the patcher, run it with your own jar&rdquo; approach follows the Eaglercraft 26.2 patcher.</dd>
</dl>

<h2>Projects it builds on</h2>
<table class="vt">
<thead><tr><th>Project</th><th>Authors</th><th>Licence</th><th>Used for</th></tr></thead>
<tbody>
<tr><td class="ver">Eaglercraft 26.2 patcher</td><td>o_xer</td><td>as published by its author</td><td>The patcher framework the 26.2 package builds from.</td></tr>
<tr><td class="ver"><a href="https://github.com/Vineflower/vineflower">Vineflower</a></td><td>The Vineflower contributors</td><td>Apache-2.0</td><td>Decompiler, run on your machine.</td></tr>
<tr><td class="ver"><a href="https://github.com/konsoletyper/teavm">TeaVM</a></td><td>Alexey Andreev and contributors</td><td>Apache-2.0</td><td>Compiles Java to WebAssembly and JavaScript.</td></tr>
<tr><td class="ver">Eaglercraft and EaglercraftX</td><td>lax1dude, ayunami2000 and contributors</td><td>their own terms</td><td>Minecraft in the browser.</td></tr>
<tr><td class="ver"><a href="https://asm.ow2.io/">ASM</a></td><td>OW2 Consortium</td><td>BSD-3-Clause</td><td>Bytecode remapping.</td></tr>
</tbody></table>

<h2>Older versions (in progress)</h2>
<p>The patchers for 1.12, 1.14 and 1.16.5 are being rebuilt by comparing existing Eaglercraft sources with the official game. These are the sources they are compared against; each one's licence is checked and listed with its version before that version is released.</p>
<table class="vt">
<thead><tr><th>Version</th><th>Source</th><th>Credit as stated by the source</th></tr></thead>
<tbody>
<tr><td class="ver">1.14</td><td><a href="https://github.com/Eagler-Versions/eaglercraft-1.14-workspace">Eagler-Versions/eaglercraft-1.14-workspace</a></td><td>&ldquo;Ported by EYMENWSMC&rdquo;; the Gradle plugin is by cire3.</td></tr>
<tr><td class="ver">1.12</td><td><a href="https://github.com/DevevolperPlus/Eaglercraft-1.12-Source">DevevolperPlus/Eaglercraft-1.12-Source</a></td><td>Eaglercraft 1.12 project by catfoolyou (repository hosted by DevevolperPlus).</td></tr>
<tr><td class="ver">1.16.5</td><td>Autopatcher's own port</td><td>Built here from the official client.</td></tr>
</tbody></table>

<h2>Development tools</h2>
<p>Used while building the patchers, never shipped inside a release: JavaParser (Apache-2.0 or LGPL-3.0), SpecialSource, and the Mod Coder Pack mapping data used to read the older Eaglercraft sources. Mapping data and Mojang's files are fetched onto your own computer and are not republished here.</p>

<h2>Missing a credit?</h2>
<p>If you wrote something this project uses and your credit is missing or wrong, tell us on the <a href="https://github.com/pxdns/autopatcherbuild/issues">issue tracker</a> and it will be fixed.</p>
''', "credits.html")

# ---------------------------------------------------------------- legal overview
page("legal.html", "Legal &middot; Autopatcher", "Licence, copyright policy, privacy and disclaimers for Autopatcher.", f'''
<section class="intro"><div class="eyebrow">Legal</div><h1>Legal</h1>
<p class="lead" style="margin:0">What this project contains, how it is licensed, and where to send a copyright report. Last updated {UPDATED}. Not legal advice.</p></section>

<h2>What this project does and does not contain</h2>
<dl class="facts">
<dt>Contains</dt><dd>The run scripts, the Java patcher, the tools, this site and the docs.</dd>
<dt>Does not contain</dt><dd>Minecraft code, decompiled Minecraft source, Minecraft assets, or a built client.</dd>
<dt>A release holds</dt><dd>The patcher program and a patch bundle: new files written for this project, plus changes that consist only of added lines. Removed or replaced original lines are recorded as hashes, never as text.</dd>
<dt>Checked by</dt><dd>Every build runs a leak scan that fails if the bundle contains a run of lines copied from Minecraft's decompiled code.</dd>
<dt>You supply</dt><dd>Your own copy of the game. The run script downloads Mojang's official client jar and mappings straight from Mojang's servers onto your computer and checks their SHA-1 values. They are never uploaded or republished here.</dd>
<dt>What you build</dt><dd>A client you generate contains Minecraft's code and files. Keep it for your own use unless you have the right to distribute it.</dd>
</dl>
<p style="margin-top:14px">This is how the project is designed to respect Mojang's terms. It is not legal advice and not a guarantee.</p>

<h2>The legal pages</h2>
<div class="cols">
<div class="box"><h3><a href="licence.html">Licence</a></h3><p>GPL-3.0-or-later with a permission for combining with Minecraft, and third-party licences.</p></div>
<div class="box"><h3><a href="dmca.html">Copyright / DMCA</a></h3><p>Who owns what, how to report an infringement, and how to dispute a report.</p></div>
<div class="box"><h3><a href="privacy.html">Privacy</a></h3><p>What this website and the patcher do and do not collect.</p></div>
</div>

<h2>Trademarks and affiliation</h2>
<p>Minecraft is a trademark of Mojang Studios, part of Microsoft. Autopatcher is unofficial and is not affiliated with, endorsed by or sponsored by Mojang or Microsoft. The Autopatcher name and icon are original artwork covered by the GPL like the rest of the project's own files, but they give you no right to imply that a fork is the official project. Other names belong to their owners.</p>

<h2>No warranty</h2>
<p>The software is provided as it is, without warranty of any kind, as set out in the GPL. You are responsible for following the licences and terms that apply to the game and to anything you build or share.</p>
''', "legal.html", legal=True)

# ---------------------------------------------------------------- licence
page("licence.html", "Licence &middot; Autopatcher", "How Autopatcher is licensed.", f'''
<section class="intro"><div class="eyebrow">Legal</div><h1>Licence</h1>
<p class="lead" style="margin:0">Last updated {UPDATED}. Not legal advice.</p></section>

<h2>Autopatcher's own code</h2>
<p>The run scripts, the Java patcher, the tools, this site and the docs are licensed under the GNU General Public License, version 3 or (at your option) any later version, with an additional permission for combining with Minecraft. Copyright (C) 2026 The Autopatcher contributors. Created by murd.er.</p>
<p>The full texts are in the repository: <a href="https://github.com/pxdns/autopatcherbuild/blob/main/LICENSE">LICENSE</a> and <a href="https://github.com/pxdns/autopatcherbuild/blob/main/LICENSE-EXCEPTION.txt">LICENSE-EXCEPTION.txt</a>.</p>

<h2>The additional permission, in short</h2>
<p>If you modify this program by linking or combining it with Minecraft: Java Edition (or a modified version of it, including one produced by decompiling it and applying this program's patches), the licensors give you permission to convey the result. The Corresponding Source for a non-source form of such a combination must include the source of the parts of this program used, but need not include the source of the Minecraft parts.</p>
<p>This covers only the Minecraft parts of such a combination. It gives you no rights in Minecraft itself, which you must get from Mojang Studios under their own terms, and it does not change the licence of any other component. The wording in <code>LICENSE-EXCEPTION.txt</code> is the one that applies.</p>

<h2>Everything else keeps its own licence</h2>
<p>What Autopatcher downloads or builds on keeps its own licence and authors. They are listed on the <a href="credits.html">credits page</a> and in <a href="https://github.com/pxdns/autopatcherbuild/blob/main/NOTICE.md">NOTICE.md</a>. Minecraft's code, textures, sounds, text, name and logo belong to Mojang Studios and Microsoft and are used under their terms, not this project's.</p>

<h2>Name and icon</h2>
<p>The Autopatcher name and icon are original artwork covered by the GPL like the rest of the project's own files. They give you no right to present a fork as the official project or to remove the notices and the &ldquo;unofficial, not affiliated with Mojang or Microsoft&rdquo; statement.</p>
''', "licence.html", legal=True)

# ---------------------------------------------------------------- dmca
page("dmca.html", "Copyright / DMCA &middot; Autopatcher", "Who owns what in Autopatcher, how to report an infringement, and how to dispute a report.", f'''
<section class="intro"><div class="eyebrow">Legal</div><h1>Copyright and takedown policy</h1>
<p class="lead" style="margin:0">Last updated {UPDATED}. This explains who owns what, how to report material you believe infringes your copyright, and how to dispute a report made in error. It is written in plain language. It is not legal advice and it does not decide whether any particular file may lawfully be distributed.</p></section>

<h2>1. Scope</h2>
<p>Autopatcher is an unofficial open-source project, published at <a href="{REPO}">github.com/pxdns/autopatcherbuild</a>, with this website. This policy covers the repository, its releases and this site. It does not cover third-party servers, packs or mods hosted elsewhere, the other repositories Autopatcher builds on, or Minecraft itself.</p>
<p>We do not host uploads from the public. We still follow the principles of the United States Digital Millennium Copyright Act (DMCA) so that rights holders have a clear way to reach us. Following that process does not mean we claim, or have been found to have, any legal protection under that law.</p>

<h2>2. Who owns what</h2>
<table class="vt">
<thead><tr><th>Material</th><th>Owner</th><th>Terms</th></tr></thead>
<tbody>
<tr><td>Autopatcher's own code, tools, site and docs</td><td>The Autopatcher contributors (created by murd.er)</td><td>GPL-3.0-or-later with the permission in <code>LICENSE-EXCEPTION.txt</code></td></tr>
<tr><td>The Autopatcher name and icon</td><td>The project</td><td>Covered by the GPL; no right to imply an official fork</td></tr>
<tr><td>Minecraft: code, textures, sounds, text, name and logo</td><td>Mojang Studios and Microsoft</td><td>Their own terms. This project is not affiliated with or endorsed by either</td></tr>
<tr><td>Vineflower, TeaVM, ASM, Eaglercraft and the other projects it builds on</td><td>Their authors</td><td>Their own licences, listed on the <a href="credits.html">credits page</a></td></tr>
</tbody></table>
<p style="margin-top:14px">Nothing in the repository or on this site gives you any right in Minecraft. You must own the game and follow Mojang's and Microsoft's terms.</p>

<h2>3. What this project hosts</h2>
<p>A release contains the patcher program and a patch bundle. The bundle is built to hold no Minecraft code: new files written for this project, plus changes made only of added lines, with removed original lines recorded as hashes. Every build runs a leak scan that fails if the bundle contains a run of lines copied from Minecraft's decompiled code. The official game files are downloaded by you, from Mojang, onto your own computer. If you believe a release still contains your material, use the process below.</p>

<h2>4. How to file a copyright notice</h2>
<ol class="steps">
<li><div class="c"><b>Confirm you can act</b><span>You must own the right, be an exclusive licensee, or be authorised in writing by the owner. Keep the proof: a registration, a licence or assignment, dated source files, or a signed letter of authority.</span></div></li>
<li><div class="c"><b>Check the use is not authorised</b><span>Look at the licence files and the <a href="credits.html">credits</a>. A use that follows an open-source licence you granted is not infringement. Consider whether the use might be a fair use or other permitted exception before sending a notice; a notice sent without that thought can be challenged as a misrepresentation (section 7).</span></div></li>
<li><div class="c"><b>Identify exactly what you object to</b><span>Give the file path or page address and a permalink to the commit or release asset, and say which of your works it copies. Vague requests cannot be acted on and will be returned.</span></div></li>
<li><div class="c"><b>Gather evidence</b><span>Link the original work, add a side-by-side comparison or file hashes showing the copy, and your proof from step 1. Do not send passwords, keys or private data.</span></div></li>
<li><div class="c"><b>Send it</b><span>To us: open an issue titled &ldquo;Copyright notice&rdquo; on the <a href="https://github.com/pxdns/autopatcherbuild/issues">issue tracker</a>, or contact the maintainer privately through the GitHub profile <a href="https://github.com/pxdns">pxdns</a> if the notice has personal details. To the host: use GitHub's own DMCA form. You may send it to both.</span></div></li>
<li><div class="c"><b>Write the notice</b><span>Include: your full legal name, address and a way to reach you, with your signature (typed is fine); the work you say was infringed; the exact locations of the infringing material; a statement that you believe in good faith that the use is not authorised by you, your agent or the law; and a statement, under penalty of perjury, that the notice is accurate and that you are the owner or authorised to act.</span></div></li>
</ol>

<h2>5. What we do when we receive a notice</h2>
<ul>
<li>We read it and, if it is complete, remove or disable the material identified, or tell you why we cannot. If it is incomplete we ask for what is missing.</li>
<li>We tell the person responsible for the material, where we can, and give them a copy of the notice with your contact details removed where the law allows.</li>
<li>If material is removed in error, we restore it as soon as the question is settled.</li>
</ul>

<h2>6. How to dispute a report (counter-notice)</h2>
<p>If material of yours was removed and you believe that was a mistake or a misidentification, send us a counter-notice in the same way: your name, address and contact details; the material and where it was before removal; a statement under penalty of perjury that you believe in good faith it was removed by mistake; and your agreement to the jurisdiction that applies to you. We may restore the material unless the rights holder tells us they have started legal action.</p>

<h2>7. False or abusive reports</h2>
<p>Knowingly sending a false notice or counter-notice can have legal consequences. We may ignore reports that are bulk, automated or plainly unrelated to this project.</p>

<h2>8. Repeat infringement</h2>
<p>We may remove contributors' access or stop distributing material from anyone who repeatedly infringes.</p>

<h2>9. Notices from Mojang or Microsoft</h2>
<p>If Mojang Studios or Microsoft tell us that something here does not meet their terms, we take it seriously and act on it promptly. Use the same route as above.</p>
''', "dmca.html", legal=True)

# ---------------------------------------------------------------- privacy
page("privacy.html", "Privacy &middot; Autopatcher", "What this website and the patcher collect.", f'''
<section class="intro"><div class="eyebrow">Legal</div><h1>Privacy</h1>
<p class="lead" style="margin:0">Last updated {UPDATED}. Short version: this site keeps no accounts and no tracking.</p></section>

<h2>This website</h2>
<ul>
<li><b>No accounts, no cookies, no analytics, no advertising.</b> The site is static files.</li>
<li><b>Hosting.</b> It is served by Vercel, which keeps ordinary server logs (such as your IP address and the page requested) under its own privacy policy.</li>
<li><b>GitHub.</b> The Versions page and the build-status bar fetch data from the GitHub API (<code>api.github.com</code>) in your browser, so GitHub sees your IP address and browser details, under its own privacy policy. Downloads come from GitHub Releases.</li>
<li><b>Your browser.</b> If you press the theme button, your choice (&ldquo;light&rdquo; or &ldquo;dark&rdquo;) is saved in your browser's local storage. It is never sent anywhere.</li>
</ul>

<h2>The patcher</h2>
<ul>
<li>It runs on your computer. Your client jar and what you build stay on your computer and are never uploaded to us.</li>
<li>To build, it downloads Mojang's official client jar and mappings directly from Mojang's servers, which see the request as they would for any download.</li>
</ul>

<h2>Contact</h2>
<p>Questions about this policy: open an issue on the <a href="https://github.com/pxdns/autopatcherbuild/issues">issue tracker</a>.</p>
''', "privacy.html", legal=True)

# ---------------------------------------------------------------- about (kept for old links)
page("about.html", "About &middot; Autopatcher", "About Autopatcher.", '''
<section class="intro"><div class="eyebrow">About</div><h1>About Autopatcher</h1>
<p class="lead" style="margin:0">Created by <b>murd.er</b>. It builds Eaglercraft browser clients from your own official Minecraft jar.</p></section>
<div class="cols">
<div class="box"><h3><a href="credits.html">Credits</a></h3><p>Who made it and what it builds on.</p></div>
<div class="box"><h3><a href="legal.html">Legal</a></h3><p>Licence, copyright policy and privacy.</p></div>
</div>
''', "about.html")
print("wrote", len(os.listdir(SITE)), "files in site/")
