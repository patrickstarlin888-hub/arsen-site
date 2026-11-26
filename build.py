"""Build the Arsen static site.

Usage:  python build.py
Input:  site.yaml, content/products/*.md, content/pages/*.md, static/
Output: dist/  (upload this folder to the server)
"""
import html
import json
import shutil
from datetime import date
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE = yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8"))
BASE = SITE["domain"].rstrip("/")
TODAY = date.today().isoformat()
esc = html.escape


def load(folder):
    items = []
    for f in sorted((ROOT / "content" / folder).glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm)
        meta["body_md"] = body.strip().replace("{email}", SITE["email"])
        meta["body_html"] = markdown.markdown(meta["body_md"], extensions=["tables"])
        items.append(meta)
    return items


PRODUCTS = load("products")
PAGES = {p["slug"]: p for p in load("pages")}
INDUSTRIES = load("industries")
APPLICATIONS = sorted(load("applications"), key=lambda a: a.get("order", 99))
CATEGORIES = SITE.get("categories", [])
_listed = [c["name"] for c in CATEGORIES]
CATS = _listed + sorted({p["category"] for p in PRODUCTS} - set(_listed))
CAT_SUMMARY = {c["name"]: c.get("summary", "") for c in CATEGORIES}
BY_SLUG = {p["slug"]: p for p in PRODUCTS}


def in_cat(c):
    return [p for p in PRODUCTS if p["category"] == c]
NAV = [("/products/", "Products"), ("/applications/", "Applications"),
       ("/industries/", "Industries"), ("/oem-odm/", "OEM / ODM"), ("/about/", "About")]


def tagged(key, slug):
    return [p for p in PRODUCTS if slug in p.get(key, [])]


def layout(title, description, path, content, jsonld=None, full=False):
    url = BASE + path
    nav = "".join(f'<a href="{h}">{t}</a>' for h, t in NAV)
    shop = (f'<a href="{esc(SITE["shop_url"])}">Shop</a>' if SITE.get("shop_url") else "")
    shop += '<a class="btn" href="/contact/">Request a quote</a>'
    fcol = lambda t, items: f"<div><h4>{t}</h4>" + "".join(
        f'<a href="{h}">{esc(n)}</a>' for h, n in items) + "</div>"
    foot_cols = (fcol("Products", [("/products/#" + slugify(c), c) for c in CATS]) +
                 fcol("Applications", [(f"/applications/{a['slug']}/", a["title"]) for a in APPLICATIONS]) +
                 fcol("Industries", [(f"/industries/{i['slug']}/", i["title"]) for i in INDUSTRIES]) +
                 fcol("Company", [("/oem-odm/", "OEM / ODM"), ("/about/", "About"),
                                  ("/contact/", "Contact"), ("/llms.txt", "llms.txt (for AI)")]))
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>'
                 for j in (jsonld or []))
    full_title = title if title == SITE["name"] else f"{title} | {SITE['name']}"
    return f"""<!doctype html>
<html lang="{SITE['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}">{'<meta name="robots" content="noindex">' if SITE.get('noindex') else ''}
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="stylesheet" href="/style.css">
{ld}
</head>
<body>
<header class="top"><div class="wrap">
<a class="logo" href="/"><img src="/logo-mark.png" alt="" width="34" height="34">{esc(SITE["name"].split()[0].upper())}<span>{esc(" ".join(SITE["name"].split()[1:]).upper())}</span></a>
<nav>{nav}{shop}</nav>
</div></header>
{"<main>" + content + "</main>" if full else "<main class=\"wrap pad\">" + content + "</main>"}
<section class="cta-band"><div class="wrap">
<div><h2>Have a finishing problem?</h2>
<p>Send us your material, a photo or a sample. We will recommend a product or develop one for you.</p></div>
<a class="btn light" href="/contact/">Talk to us</a></div></section>
<footer><div class="wrap">
<div class="fcols">{foot_cols}</div>
<p class="small">© {date.today().year} {esc(SITE['company'])} · Taiwan · <a href="mailto:{SITE['email']}">{SITE['email']}</a> · <a href="/sitemap.xml">Sitemap</a></p>
</div></footer>
</body>
</html>"""


def slugify(t):
    return "".join(c if c.isalnum() else "-" for c in t.lower()).strip("-")


def tile(href, title, summary, extra=""):
    return f'<a class="tile" href="{href}"><h3>{esc(title)}</h3><p>{esc(summary)}</p>{extra}<span class="more">Learn more →</span></a>'


def write(path, text):
    out = DIST / path.lstrip("/")
    if path.endswith("/"):
        out = out / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def org_ld():
    return {"@context": "https://schema.org", "@type": "Organization",
            "name": SITE["company"], "url": BASE, "email": SITE["email"],
            "description": SITE["description"]}


def sample_badge(p):
    return '<span class="badge">Sample data</span>' if p.get("sample") else ""


def product_card(p):
    img = p.get("images", [None])[0]
    pic = f'<img src="/img/{img}" alt="{esc(p["title"])}" loading="lazy">' if img else '<div class="ph">Photo coming soon</div>'
    return f"""<a class="card pcard" href="/products/{p['slug']}/">{pic}<div class="pc-body">
<span class="cat">{esc(p['category'])}</span>
<h3>{esc(p['title'])}</h3><p>{esc(p['summary'])}</p>{sample_badge(p)}</div></a>"""


def build_product(p):
    path = f"/products/{p['slug']}/"
    specs = "".join(f"<tr><th>{esc(k)}</th><td>{esc(str(v))}</td></tr>" for k, v in p["specs"])
    apps = "".join(f"<li>{esc(a)}</li>" for a in p.get("uses", []))
    faq = "".join(f"<details><summary>{esc(f['q'])}</summary><p>{esc(f['a'])}</p></details>"
                  for f in p.get("faq", []))
    links = "".join(f'<a class="tag" href="/industries/{i["slug"]}/">{esc(i["title"])}</a>'
                    for i in INDUSTRIES if i["slug"] in p.get("industries", []))
    links += "".join(f'<a class="tag" href="/applications/{a["slug"]}/">{esc(a["title"])}</a>'
                     for a in APPLICATIONS if a["slug"] in p.get("applications", []))
    buy = (f'<a class="btn" href="{esc(p["shopify_url"])}">Buy online</a>' if p.get("shopify_url")
           else '<a class="btn" href="/contact/">Request a quote</a>')
    ims = p.get("images", [])
    if ims:
        thumbs = "".join(f'<button type="button" class="thumb" onclick="document.getElementById(\'mainimg\').src=\'/img/{i}\'"><img src="/img/{i}" alt="" loading="lazy"></button>' for i in ims) if len(ims) > 1 else ""
        img = f'<img id="mainimg" src="/img/{ims[0]}" alt="{esc(p["title"])}"><div class="thumbs">{thumbs}</div>'
    else:
        img = '<div class="ph">Photo coming soon</div>'
    variants = "".join(f"<tr><th>{esc(a)}</th><td>{esc(b_)}</td></tr>" for a, b_ in p.get("variants", []))
    content = f"""<p class="crumb"><a href="/products/">Products</a> / {esc(p['category'])}</p>
<div class="hero-p">
<div>{img}</div>
<div><h1>{esc(p['title'])} {sample_badge(p)}</h1>
<p class="lead">{esc(p['summary'])}</p>
<p class="sku">SKU: {esc(p['sku'])}</p>
<p>{buy} <a class="btn ghost" href="/oem-odm/">Custom / OEM</a></p></div>
</div>
{'<h2>Types</h2><table class="specs">' + variants + '</table>' if variants else ''}
<h2>Specifications</h2><table class="specs">{specs}</table>
{'<p class="small">' + esc(p["specs_note"]) + '</p>' if p.get("specs_note") else ''}
<h2>Typical uses</h2><ul>{apps}</ul>
<p class="tags">{links}</p>
<h2>Details</h2>{p['body_html']}
{'<h2>FAQ</h2>' + faq if faq else ''}
<p class="small"><a href="/products/{p['slug']}.md">Plain-text version for AI and tools</a></p>"""
    ld = [{"@context": "https://schema.org", "@type": "Product", "name": p["title"],
           "sku": p["sku"], "category": p["category"], "description": p["summary"],
           "brand": {"@type": "Brand", "name": SITE["name"]}, "url": BASE + path,
           "image": [f"{BASE}/img/{i}" for i in p.get("images", [])],
           "additionalProperty": [{"@type": "PropertyValue", "name": k, "value": str(v)}
                                  for k, v in p["specs"]]}]
    if p.get("faq"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage",
                   "mainEntity": [{"@type": "Question", "name": f["q"],
                                   "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                                  for f in p["faq"]]})
    write(path, layout(p["title"], p["summary"], path, content, ld))
    write(f"/products/{p['slug']}.md", product_md(p))
    return path


def product_md(p):
    lines = [f"# {p['title']}", "", p["summary"], "",
             f"- SKU: {p['sku']}", f"- Category: {p['category']}",
             f"- Web page: {BASE}/products/{p['slug']}/"]
    if p.get("shopify_url"):
        lines.append(f"- Buy: {p['shopify_url']}")
    if p.get("variants"):
        lines += ["", "## Types", ""] + [f"- {a}: {d}" for a, d in p["variants"]]
    lines += ["", "## Specifications", ""] + [f"- {k}: {v}" for k, v in p["specs"]]
    if p.get("specs_note"):
        lines += ["", p["specs_note"]]
    if p.get("uses"):
        lines += ["", "## Typical uses", ""] + [f"- {a}" for a in p["uses"]]
    names = {a["slug"]: a["title"] for a in APPLICATIONS} | {i["slug"]: i["title"] for i in INDUSTRIES}
    if p.get("applications"):
        lines += ["", "Processes: " + ", ".join(names.get(a, a) for a in p["applications"])]
    if p.get("industries"):
        lines += ["Industries: " + ", ".join(names.get(a, a) for a in p["industries"])]
    if p.get("images"):
        lines += ["", "Photos: " + ", ".join(f"{BASE}/img/{i}" for i in p["images"])]
    lines += ["", "## Details", "", p["body_md"]]
    if p.get("faq"):
        lines += ["", "## FAQ", ""]
        for f in p["faq"]:
            lines += [f"**Q: {f['q']}**", f"A: {f['a']}", ""]
    return "\n".join(lines).strip() + "\n"


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST)
    urls = ["/"]

    def cat_tile(c):
        n = len(in_cat(c))
        extra = f'<span class="count">{n} product{"s" if n != 1 else ""}</span>' if n else \
                '<span class="count ask">Available on request</span>'
        items = in_cat(c)
        href = f"/products/{items[0]['slug']}/" if len(items) == 1 else f"/products/#{slugify(c)}"
        img = items[0].get("images", [None])[0] if items else None
        pic = f'<img src="/img/{img}" alt="{esc(c)}" loading="lazy">' if img else '<div class="ph">Photo coming soon</div>'
        return f'<a class="ctile" href="{href}">{pic}<div><h3>{esc(c)}</h3><p>{esc(CAT_SUMMARY.get(c, ""))}</p></div></a>'

    cat_tiles = "".join(cat_tile(c) for c in CATS)
    steps = "".join(f'<a class="step" href="/applications/{a["slug"]}/"><span class="num">{n:02d}</span>'
                    f'<h3>{esc(a["title"])}</h3><p>{esc(a["summary"])}</p></a>'
                    for n, a in enumerate(APPLICATIONS, 1))
    combos = ""
    for cb in SITE.get("combinations", []):
        items = [BY_SLUG[x] for x in cb["products"] if x in BY_SLUG]
        flow = '<span class="arrow">→</span>'.join(
            f'<a href="/products/{x["slug"]}/"><small>Step {k}</small>{esc(x["title"])}</a>'
            for k, x in enumerate(items, 1))
        combos += f'<div class="combo"><h3>{esc(cb["title"])}</h3><p>{esc(cb["summary"])}</p><div class="flow">{flow}</div></div>'
    ind_tiles = "".join(tile(f"/industries/{i['slug']}/", i["title"], i["summary"]) for i in INDUSTRIES)
    home = f"""<section class="hero"><div class="wrap hero-grid"><div>
<p class="eyebrow">Abrasives · Buffing · Pneumatic tools</p>
<h1>{esc(SITE['tagline'])}</h1>
<p class="lead">{esc(SITE['description'])}</p>
<p><a class="btn light" href="/products/">Browse products</a>
<a class="btn ghost light" href="/oem-odm/">OEM / ODM service</a></p></div>
<div class="hero-img"><img src="/img/at-702c.jpg" alt="Arsen AT-702C mini angle grinder with flap disc"></div></div></section>
<div class="wrap">
<section><h2>Our products</h2><div class="cgrid">{cat_tiles}</div></section>
<section><h2>A solution for every step of metalworking</h2>
<p class="sub">Pick the process you are working on to see the right products.</p>
<div class="steps">{steps}</div></section>
{'<section><h2>Recommended combinations</h2><p class="sub">Products that work best together, in order.</p><div class="combos">' + combos + '</div></section>' if combos else ''}
<section><h2>Industries we serve</h2><div class="grid">{ind_tiles}</div></section>
<section class="why"><h2>Why work with Arsen</h2><div class="grid4">
<div><h3>Made to your spec</h3><p>Size, grit, grade, packaging and branding customised under OEM/ODM.</p></div>
<div><h3>Samples first</h3><p>Test samples on your own parts before committing to production.</p></div>
<div><h3>Supplier documents</h3><p>Qualification paperwork prepared for electronics and industrial supply chains.</p></div>
<div><h3>Direct from Taiwan</h3><p>One contact from specification to shipping. <!-- TODO: 認證、出口國家 --></p></div>
</div></section></div>"""
    write("/", layout(SITE["name"], SITE["description"], "/", home, [org_ld()], full=True))

    groups = ""
    for c in CATS:
        items = in_cat(c)
        groups += f"<h2 id='{slugify(c)}'>{esc(c)}</h2><p class='sub'>{esc(CAT_SUMMARY.get(c, ''))}</p>"
        groups += ("<div class='grid'>" + "".join(product_card(p) for p in items) + "</div>") if items else \
            "<p>Available on request — <a href='/contact/'>tell us the size and specification you need</a>.</p>"
    write("/products/", layout("Products", "Abrasives, buffing wheels and pneumatic tools from Arsen Industrial.",
                               "/products/", f"<h1>Products</h1><div class='cgrid'>{cat_tiles}</div>"))
    urls.append("/products/")
    urls += [build_product(p) for p in PRODUCTS]

    for key, items, label in (("industries", INDUSTRIES, "Industries"),
                              ("applications", APPLICATIONS, "Applications")):
        tiles = "".join(tile(f"/{key}/{i['slug']}/", i["title"], i["summary"]) for i in items)
        write(f"/{key}/", layout(label, f"{label} served by {SITE['name']}.", f"/{key}/",
                                 f"<h1>{label}</h1><div class='grid'>{tiles}</div>"))
        urls.append(f"/{key}/")
        for i in items:
            path = f"/{key}/{i['slug']}/"
            prods = tagged(key, i["slug"])
            cards = "".join(product_card(p) for p in prods) or "<p>Products coming soon.</p>"
            body = (f"<p class='crumb'><a href='/{key}/'>{label}</a></p><h1>{esc(i['title'])}</h1>"
                    f"<p class='lead'>{esc(i['summary'])}</p>{i['body_html']}"
                    f"<h2>Recommended products</h2><div class='grid'>{cards}</div>")
            write(path, layout(i["title"], i["summary"], path, body))
            md = f"# {i['title']}\n\n{i['body_md']}\n\n## Recommended products\n\n" + \
                 "".join(f"- [{p['title']}]({BASE}/products/{p['slug']}.md): {p['summary']}\n" for p in prods)
            write(f"/{key}/{i['slug']}.md", md)
            urls.append(path)

    for slug, pg in PAGES.items():
        path = f"/{slug}/"
        write(path, layout(pg["title"], pg["summary"], path,
                           f"<h1>{esc(pg['title'])}</h1>{pg['body_html']}"))
        write(f"/{slug}.md", f"# {pg['title']}\n\n{pg['body_md']}\n")
        urls.append(path)

    # llms.txt — index for AI assistants (llmstxt.org format)
    llms = [f"# {SITE['name']}", "", f"> {SITE['description']}", "",
            f"Contact: {SITE['email']}", "", "## Products", ""]
    llms += [f"- [{p['title']}]({BASE}/products/{p['slug']}.md): {p['summary']}" for p in PRODUCTS]
    for key, items, label in (("applications", APPLICATIONS, "Applications"),
                              ("industries", INDUSTRIES, "Industries")):
        llms += ["", f"## {label}", ""]
        llms += [f"- [{i['title']}]({BASE}/{key}/{i['slug']}.md): {i['summary']}" for i in items]
    llms += ["", "## Company", ""]
    llms += [f"- [{pg['title']}]({BASE}/{s}.md): {pg['summary']}" for s, pg in PAGES.items()]
    write("/llms.txt", "\n".join(llms) + "\n")
    full = [f"# {SITE['name']} — full product information", "", SITE["description"], ""]
    full += [product_md(p) for p in PRODUCTS]
    full += [f"# {pg['title']}\n\n{pg['body_md']}\n" for pg in PAGES.values()]
    write("/llms-full.txt", "\n---\n\n".join(full))

    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) +
          "</urlset>\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    write("/404.html", layout("Page not found", "Page not found", "/404.html",
                              "<h1>Page not found</h1><p><a href='/'>Back to home</a></p>"))
    print(f"Built {len(PRODUCTS)} products, {len(PAGES)} pages -> {DIST}")


if __name__ == "__main__":
    build()
